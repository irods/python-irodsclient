from __future__ import absolute_import
import os
import io
from irods.models import DataObject
from irods.manager import Manager
from irods.message import (
    iRODSMessage, FileOpenRequest, ObjCopyRequest, StringStringMap, DataObjInfo, ModDataObjMeta,
    DataObjChksumRequest, DataObjChksumResponse)
import irods.exception as ex
from irods.api_number import api_number
from irods.data_object import (
    iRODSDataObject, iRODSDataObjectFileRaw, chunks, irods_dirname, irods_basename)
import irods.keywords as kw
import irods.parallel as parallel
import six
import ast


MAXIMUM_SINGLE_THREADED_TRANSFER_SIZE = 32 * ( 1024 ** 2)

DEFAULT_NUMBER_OF_THREADS = 0   # Defaults for reasonable number of threads -- optimized to be
                                # performant but allow no more worker threads than available CPUs.
                                # Setting this to 1 disables automatic use of parallel transfer.
DEFAULT_QUEUE_DEPTH = 32

class DataObjectManager(Manager):

    READ_BUFFER_SIZE = 1024 * io.DEFAULT_BUFFER_SIZE
    WRITE_BUFFER_SIZE = 1024 * io.DEFAULT_BUFFER_SIZE

    # Data object open flags (independent of client os)
    O_RDONLY = 0
    O_WRONLY = 1
    O_RDWR = 2
    O_APPEND = 1024
    O_CREAT = 64
    O_EXCL = 128
    O_TRUNC = 512


    def should_parallelize_transfer( self,
                                     num_threads = 0,
                                     obj_sz = 1+MAXIMUM_SINGLE_THREADED_TRANSFER_SIZE,
                                     server_version_hint = ()):
        # Allow an environment variable to override the detection of the server version.
        # Example: $ export IRODS_VERSION_OVERRIDE="4,2,9" ;  python -m irods.parallel ...
        server_version = ( ast.literal_eval(os.environ.get('IRODS_VERSION_OVERRIDE', '()' )) or server_version_hint or 
                           self.server_version )
        if num_threads == 1 or ( server_version < parallel.MINIMUM_SERVER_VERSION ):
            return False
        if getattr(obj_sz,'seek',None) :
            pos = obj_sz.tell()
            size = obj_sz.seek(0,os.SEEK_END)
            if not isinstance(size,six.integer_types):
                size = obj_sz.tell()
            obj_sz.seek(pos,os.SEEK_SET)
        else:
            size = obj_sz
            assert (size > -1)
        return size > MAXIMUM_SINGLE_THREADED_TRANSFER_SIZE


    def _download(self, obj, local_path, num_threads, **options):

        if os.path.isdir(local_path):
            local_file = os.path.join(local_path, irods_basename(obj))
        else:
            local_file = local_path

        # Check for force flag if local_file exists
        if os.path.exists(local_file) and kw.FORCE_FLAG_KW not in options:
            raise ex.OVERWRITE_WITHOUT_FORCE_FLAG

        with open(local_file, 'wb') as f, self.open(obj, 'r', **options) as o:

            if self.should_parallelize_transfer (num_threads, o):
                f.close()
                if not self.parallel_get( (obj,o), local_path, num_threads = num_threads,
                                          target_resource_name = options.get(kw.RESC_NAME_KW,'')):
                    raise RuntimeError("parallel get failed")
            else:
                for chunk in chunks(o, self.READ_BUFFER_SIZE):
                    f.write(chunk)


    def get(self, path, local_path = None, num_threads = DEFAULT_NUMBER_OF_THREADS, **options):
        parent = self.sess.collections.get(irods_dirname(path))

        # TODO: optimize
        if local_path:
            self._download(path, local_path, num_threads = num_threads, **options)

        query = self.sess.query(DataObject)\
            .filter(DataObject.name == irods_basename(path))\
            .filter(DataObject.collection_id == parent.id)\
            .add_keyword(kw.ZONE_KW, path.split('/')[1])

        results = query.all() # get up to max_rows replicas
        if len(results) <= 0:
            raise ex.DataObjectDoesNotExist()
        return iRODSDataObject(self, parent, results)


    def put(self, local_path, irods_path, return_data_object = False, num_threads = DEFAULT_NUMBER_OF_THREADS, **options):

        if irods_path.endswith('/'):
            obj = irods_path + os.path.basename(local_path)
        else:
            obj = irods_path

        with open(local_path, 'rb') as f, self.open(obj, 'w', **options) as o:

            if self.should_parallelize_transfer (num_threads, f):
                f.close()
                if not self.parallel_put( local_path, (obj,o), num_threads = num_threads,
                                          target_resource_name = options.get(kw.RESC_NAME_KW,'') or
                                                                 options.get(kw.DEST_RESC_NAME_KW,'')):
                    raise RuntimeError("parallel put failed")
            else:
                # Set operation type to trigger acPostProcForPut
                if kw.OPR_TYPE_KW not in options:
                    options[kw.OPR_TYPE_KW] = 1 # PUT_OPR
                for chunk in chunks(f, self.WRITE_BUFFER_SIZE):
                    o.write(chunk)

        if kw.ALL_KW in options:
            options[kw.UPDATE_REPL_KW] = ''
            self.replicate(obj, **options)

        if return_data_object:
            return self.get(obj)

    def chksum(self, path, **options):
        message_body = DataObjChksumRequest(path, **options)
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_CHKSUM_AN'])
        checksum = None
        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
            results = response.get_main_message(DataObjChksumResponse)
            checksum = results.myStr
        return checksum


    def parallel_get(self,
                     data_or_path_ ,
                     file_ ,
                     async_ = False,
                     num_threads = 0,
                     target_resource_name = '',
                     progressQueue = False):

        return parallel.io_main( self.sess, data_or_path_, parallel.Oper.GET | (parallel.Oper.NONBLOCKING if async_ else 0), file_,
                                 num_threads = num_threads, target_resource_name = target_resource_name,
                                 queueLength = (DEFAULT_QUEUE_DEPTH if progressQueue else 0))

    def parallel_put(self,
                     file_ ,
                     data_or_path_ ,
                     async_ = False,
                     num_threads = 0,
                     target_resource_name = '',
                     progressQueue = False):

        return parallel.io_main( self.sess, data_or_path_, parallel.Oper.PUT | (parallel.Oper.NONBLOCKING if async_ else 0), file_,
                                 num_threads = num_threads, target_resource_name = target_resource_name,
                                 queueLength = (DEFAULT_QUEUE_DEPTH if progressQueue else 0))


    def create(self, path, resource=None, force=False, **options):
        options[kw.DATA_TYPE_KW] = 'generic'

        if resource:
            options[kw.DEST_RESC_NAME_KW] = resource
        else:
            # Use client-side default resource if available
            try:
                options[kw.DEST_RESC_NAME_KW] = self.sess.default_resource
            except AttributeError:
                pass

        if force:
            options[kw.FORCE_FLAG_KW] = ''

        message_body = FileOpenRequest(
            objPath=path,
            createMode=0o644,
            openFlags=0,
            offset=0,
            dataSize=-1,
            numThreads=self.sess.numThreads,
            oprType=0,
            KeyValPair_PI=StringStringMap(options),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_CREATE_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
            desc = response.int_info
            conn.close_file(desc)

        return self.get(path)


    def open_with_FileRaw(self, *arg, **kw_options):
        holder = []
        handle = self.open(*arg,_raw_fd_holder=holder,**kw_options)
        return (handle, holder[-1])

    def open(self, path, mode, create = True, finalize_on_close = True, **options):
        _raw_fd_holder =  options.get('_raw_fd_holder',[])
        if kw.DEST_RESC_NAME_KW not in options:
            # Use client-side default resource if available
            try:
                options[kw.DEST_RESC_NAME_KW] = self.sess.default_resource
            except AttributeError:
                pass
        createFlag = self.O_CREAT if create else 0
        flags, seek_to_end = {
            'r': (self.O_RDONLY, False),
            'r+': (self.O_RDWR, False),
            'w': (self.O_WRONLY | createFlag | self.O_TRUNC, False),
            'w+': (self.O_RDWR | createFlag | self.O_TRUNC, False),
            'a': (self.O_WRONLY | createFlag, True),
            'a+': (self.O_RDWR | createFlag, True),
        }[mode]
        # TODO: Use seek_to_end

        try:
            oprType = options[kw.OPR_TYPE_KW]
        except KeyError:
            oprType = 0

        message_body = FileOpenRequest(
            objPath=path,
            createMode=0,
            openFlags=flags,
            offset=0,
            dataSize=-1,
            numThreads=self.sess.numThreads,
            oprType=oprType,
            KeyValPair_PI=StringStringMap(options),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_OPEN_AN'])

        conn = self.sess.pool.get_connection()
        conn.send(message)
        desc = conn.recv().int_info

        raw = iRODSDataObjectFileRaw(conn, desc, finalize_on_close = finalize_on_close, **options)
        (_raw_fd_holder).append(raw)
        return io.BufferedRandom(raw)


    def unlink(self, path, force=False, **options):
        if force:
            options[kw.FORCE_FLAG_KW] = ''

        try:
            oprType = options[kw.OPR_TYPE_KW]
        except KeyError:
            oprType = 0

        message_body = FileOpenRequest(
            objPath=path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=-1,
            numThreads=self.sess.numThreads,
            oprType=oprType,
            KeyValPair_PI=StringStringMap(options),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_UNLINK_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()


    def unregister(self, path, **options):
        # https://github.com/irods/irods/blob/4.2.1/lib/api/include/dataObjInpOut.h#L190
        options[kw.OPR_TYPE_KW] = 26

        self.unlink(path, **options)


    def exists(self, path):
        try:
            self.get(path)
        except ex.DoesNotExist:
            return False
        return True


    def move(self, src_path, dest_path):
        # check if dest is a collection
        # if so append filename to it
        if self.sess.collections.exists(dest_path):
            filename = src_path.rsplit('/', 1)[1]
            target_path = dest_path + '/' + filename
        else:
            target_path = dest_path

        src = FileOpenRequest(
            objPath=src_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=self.sess.numThreads,
            oprType=11,   # RENAME_DATA_OBJ
            KeyValPair_PI=StringStringMap(),
        )
        dest = FileOpenRequest(
            objPath=target_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=self.sess.numThreads,
            oprType=11,   # RENAME_DATA_OBJ
            KeyValPair_PI=StringStringMap(),
        )
        message_body = ObjCopyRequest(
            srcDataObjInp_PI=src,
            destDataObjInp_PI=dest
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_RENAME_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()


    def copy(self, src_path, dest_path, **options):
        # check if dest is a collection
        # if so append filename to it
        if self.sess.collections.exists(dest_path):
            filename = src_path.rsplit('/', 1)[1]
            target_path = dest_path + '/' + filename
        else:
            target_path = dest_path

        src = FileOpenRequest(
            objPath=src_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=self.sess.numThreads,
            oprType=10,   # COPY_SRC
            KeyValPair_PI=StringStringMap(),
        )
        dest = FileOpenRequest(
            objPath=target_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=self.sess.numThreads,
            oprType=9,   # COPY_DEST
            KeyValPair_PI=StringStringMap(options),
        )
        message_body = ObjCopyRequest(
            srcDataObjInp_PI=src,
            destDataObjInp_PI=dest
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_COPY_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()


    def truncate(self, path, size, **options):
        message_body = FileOpenRequest(
            objPath=path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=size,
            numThreads=self.sess.numThreads,
            oprType=0,
            KeyValPair_PI=StringStringMap(options),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_TRUNCATE_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()


    def replicate(self, path, resource=None, **options):
        if resource:
            options[kw.DEST_RESC_NAME_KW] = resource

        message_body = FileOpenRequest(
            objPath=path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=-1,
            numThreads=self.sess.numThreads,
            oprType=6,
            KeyValPair_PI=StringStringMap(options),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_REPL_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()


    def register(self, file_path, obj_path, **options):
        options[kw.FILE_PATH_KW] = file_path

        message_body = FileOpenRequest(
            objPath=obj_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=self.sess.numThreads,
            oprType=0,
            KeyValPair_PI=StringStringMap(options),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['PHY_PATH_REG_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()

    def modDataObjMeta(self, data_obj_info, meta_dict, **options):
        if "rescHier" not in data_obj_info and "rescName" not in data_obj_info and "replNum" not in data_obj_info:
            meta_dict["all"] = ""
            
        message_body = ModDataObjMeta(
            dataObjInfo=DataObjInfo(
                objPath=data_obj_info["objPath"],
                rescName=data_obj_info.get("rescName", ""),
                rescHier=data_obj_info.get("rescHier", ""),
                dataType="",
                dataSize=0,
                chksum="",
                version="",
                filePath="",
                dataOwnerName="",
                dataOwnerZone="",
                replNum=data_obj_info.get("replNum", 0),
                replStatus=0,
                statusString="",
                dataId=0,
                collId=0,
                dataMapId=0,
                flags=0,
                dataComments="",
                dataMode="",
                dataExpiry="",
                dataCreate="",
                dataModify="",
                dataAccess="",
                dataAccessInx=0,
                writeFlag=0,
                destRescName="",
                backupRescName="",
                subPath="",
                specColl=0,
                regUid=0,
                otherFlags=0,
                KeyValPair_PI=StringStringMap(options),
                in_pdmo="",
                next=0,
                rescId=0
                ),
            regParam=StringStringMap(meta_dict)
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['MOD_DATA_OBJ_META_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
