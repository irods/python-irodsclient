from __future__ import absolute_import
import os
import io
from irods.models import DataObject
from irods.manager import Manager
from irods.message import (
    iRODSMessage, FileOpenRequest, ObjCopyRequest, StringStringMap, DataObjInfo, ModDataObjMeta)
import irods.exception as ex
from irods.api_number import api_number
from irods.data_object import (
    iRODSDataObject, iRODSDataObjectFileRaw, chunks, irods_dirname, irods_basename)
import irods.keywords as kw


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

    def _download(self, obj, local_path, **options):
        if os.path.isdir(local_path):
            file = os.path.join(local_path, irods_basename(obj))
        else:
            file = local_path

        # Check for force flag if file exists
        if os.path.exists(file) and kw.FORCE_FLAG_KW not in options:
            raise ex.OVERWRITE_WITHOUT_FORCE_FLAG

        with open(file, 'wb') as f, self.open(obj, 'r', **options) as o:
            for chunk in chunks(o, self.READ_BUFFER_SIZE):
                f.write(chunk)


    def get(self, path, file=None, **options):
        parent = self.sess.collections.get(irods_dirname(path))

        # TODO: optimize
        if file:
            self._download(path, file, **options)

        query = self.sess.query(DataObject)\
            .filter(DataObject.name == irods_basename(path))\
            .filter(DataObject.collection_id == parent.id)\
            .add_keyword(kw.ZONE_KW, path.split('/')[1])

        results = query.all() # get up to max_rows replicas
        if len(results) <= 0:
            raise ex.DataObjectDoesNotExist()
        return iRODSDataObject(self, parent, results)


    def put(self, file, irods_path, return_data_object=False, **options):
        if irods_path.endswith('/'):
            obj = irods_path + os.path.basename(file)
        else:
            obj = irods_path

        # Set operation type to trigger acPostProcForPut
        if kw.OPR_TYPE_KW not in options:
            options[kw.OPR_TYPE_KW] = 1 # PUT_OPR

        with open(file, 'rb') as f, self.open(obj, 'w', **options) as o:
            for chunk in chunks(f, self.WRITE_BUFFER_SIZE):
                o.write(chunk)

        if kw.ALL_KW in options:
            options[kw.UPDATE_REPL_KW] = ''
            self.replicate(obj, **options)

        if return_data_object:
            return self.get(obj)


    def create(self, path, resource=None, **options):
        options[kw.DATA_TYPE_KW] = 'generic'

        if resource:
            options[kw.DEST_RESC_NAME_KW] = resource
        else:
            # Use client-side default resource if available
            try:
                options[kw.DEST_RESC_NAME_KW] = self.sess.default_resource
            except AttributeError:
                pass

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


    def open(self, path, mode, **options):
        if kw.DEST_RESC_NAME_KW not in options:
            # Use client-side default resource if available
            try:
                options[kw.DEST_RESC_NAME_KW] = self.sess.default_resource
            except AttributeError:
                pass

        flags, seek_to_end = {
            'r': (self.O_RDONLY, False),
            'r+': (self.O_RDWR, False),
            'w': (self.O_WRONLY | self.O_CREAT | self.O_TRUNC, False),
            'w+': (self.O_RDWR | self.O_CREAT | self.O_TRUNC, False),
            'a': (self.O_WRONLY | self.O_CREAT, True),
            'a+': (self.O_RDWR | self.O_CREAT, True),
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

        return io.BufferedRandom(iRODSDataObjectFileRaw(conn, desc, **options))


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
