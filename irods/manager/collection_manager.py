from __future__ import absolute_import
import os
import stat
import itertools
from irods.models import Collection
from irods.manager import Manager
from irods.message import iRODSMessage, CollectionRequest, FileOpenRequest, ObjCopyRequest, StringStringMap
from irods.exception import CollectionDoesNotExist, NoResultFound
from irods.api_number import api_number
from irods.collection import iRODSCollection
from irods.constants import SYS_SVR_TO_CLI_COLL_STAT, SYS_CLI_TO_SVR_COLL_STAT_REPLY
import irods.keywords as kw


class GetPathCreationError ( RuntimeError ):
    """Error denoting the failure to create a new directory for writing.
    """

def make_writable_dir_if_none_exists( path ):
    if not os.path.exists(path):
        os.mkdir(path)
    if os.path.isdir( path ):
        os.chmod(path, os.stat(path).st_mode | stat.S_IWUSR)
    if not os.path.isdir( path ) or not os.access( path, os.W_OK ):
        raise GetPathCreationError( '{!r} not a writable directory'.format(path) )

try:
    # Python 2 only
    from string import maketrans as _maketrans
except:
    _maketrans = str.maketrans

_sep2slash = _maketrans(os.path.sep,"/")
_slash2sep = _maketrans("/",os.path.sep)
_from_mswin = (lambda path: str.translate(path,_sep2slash)) if os.path.sep != '/' else (lambda x:x)
_to_mswin =   (lambda path: str.translate(path,_slash2sep)) if os.path.sep != '/' else (lambda x:x)

class CollectionManager(Manager):

    def put_recursive (self, localpath, path, abort_if_not_empty = True, **put_options):
        c = self.sess.collections.create( path )
        w = list(itertools.islice(c.walk(), 0, 2))  # dereference first 1 to 2 elements of the walk
        if abort_if_not_empty and (len(w) > 1 or len(w[0][-1]) > 0):
            raise RuntimeError('collection {path!r} exists and is non-empty'.format(**locals()))
        localpath = os.path.normpath(localpath)
        for my_dir,_,sub_files in os.walk(localpath,topdown=True):
            dir_without_prefix = os.path.relpath( my_dir, localpath )
            subcoll = self.sess.collections.create(path if dir_without_prefix == os.path.curdir
                                                        else path + "/" + _from_mswin(dir_without_prefix))
            for file_ in sub_files:
                self.sess.data_objects.put( os.path.join(my_dir,file_), subcoll.path + "/" + file_, **put_options)


    def get_recursive (self, path, localpath, abort_if_not_empty = True, **get_options):
        if os.path.isdir(localpath):
            w = list(itertools.islice(os.walk(localpath), 0, 2))
            if abort_if_not_empty and (len(w) > 1 or len(w[0][-1]) > 0):
                raise RuntimeError('local directory {localpath!r} exists and is non-empty'.format(**locals()))
        def unprefix (path,prefix=''):
            return path if not path.startswith(prefix) else path[len(prefix):]
        c = self.get(path)
        # TODO ## For a visible percent-complete status:
        #      #  nbytes = sum(d.size for el in c.walk() for d in el[2])
        #      ## (Then use eg tqdm module to create progress-bar.)
        c_prefix = c.path + "/"
        for coll,_,sub_datas in c.walk(topdown=True):
            relative_collpath = unprefix (coll.path + "/", c_prefix)
            new_target_dir = os.path.join(localpath, _to_mswin(relative_collpath))
            make_writable_dir_if_none_exists( new_target_dir )
            for data in sub_datas:
                local_data_path = os.path.join(new_target_dir, data.name)
                self.sess.data_objects.get( data.path, local_data_path, **get_options )


    def get(self, path):
        query = self.sess.query(Collection).filter(Collection.name == path)
        try:
            result = query.one()
        except NoResultFound:
            raise CollectionDoesNotExist()
        return iRODSCollection(self, result)


    def create(self, path, recurse=True, **options):
        if recurse:
            options[kw.RECURSIVE_OPR__KW] = ''
       
        message_body = CollectionRequest(
            collName=path,
            KeyValPair_PI=StringStringMap(options)
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['COLL_CREATE_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
        return self.get(path)


    def remove(self, path, recurse=True, force=False, **options):
        if recurse:
            options[kw.RECURSIVE_OPR__KW] = ''
        if force:
            options[kw.FORCE_FLAG_KW] = ''

        try:
            oprType = options[kw.OPR_TYPE_KW]
        except KeyError:
            oprType = 0

        message_body = CollectionRequest(
            collName=path,
            flags = 0,
            oprType = oprType,
            KeyValPair_PI=StringStringMap(options)
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['RM_COLL_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()

            while response.int_info == SYS_SVR_TO_CLI_COLL_STAT:
                conn.reply(SYS_CLI_TO_SVR_COLL_STAT_REPLY)
                response = conn.recv()


    def unregister(self, path, **options):
        # https://github.com/irods/irods/blob/4.2.1/lib/api/include/dataObjInpOut.h#L190
        options[kw.OPR_TYPE_KW] = 26

        self.remove(path, **options)


    def exists(self, path):
        try:
            self.get(path)
        except CollectionDoesNotExist:
            return False
        return True


    def move(self, src_path, dest_path):
        # check if dest is an existing collection
        # if so append collection name to it
        if self.sess.collections.exists(dest_path):
            coll_name = src_path.rsplit('/', 1)[1]
            target_path = dest_path + '/' + coll_name
        else:
            target_path = dest_path

        src = FileOpenRequest(
            objPath=src_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=0,
            oprType=12,   # RENAME_COLL
            KeyValPair_PI=StringStringMap(),
        )
        dest = FileOpenRequest(
            objPath=target_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=0,
            oprType=12,   # RENAME_COLL
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


    def register(self, dir_path, coll_path, **options):
        options[kw.FILE_PATH_KW] = dir_path
        options[kw.COLLECTION_KW] = ''

        message_body = FileOpenRequest(
            objPath=coll_path,
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
