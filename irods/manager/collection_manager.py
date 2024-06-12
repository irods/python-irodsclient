from __future__ import absolute_import
from irods.models import Collection, DataObject
from irods.manager import Manager
from irods.manager._internal import _api_impl
from irods.message import iRODSMessage, CollectionRequest, FileOpenRequest, ObjCopyRequest, StringStringMap
from irods.exception import CollectionDoesNotExist, NoResultFound
from irods.api_number import api_number
from irods.collection import iRODSCollection
from irods.constants import SYS_SVR_TO_CLI_COLL_STAT, SYS_CLI_TO_SVR_COLL_STAT_REPLY
import irods.keywords as kw


class CollectionManager(Manager):

    def get(self, path):
        path = iRODSCollection.normalize_path( path )
        filters = [Collection.name == path]
        # if a ticket is supplied for this session, try both without and with DataObject join
        repeats = (True,False) if hasattr(self.sess,'ticket__') \
             else (False,)
        for rep in repeats:
            query = self.sess.query(Collection).filter(*filters)
            try:
                result = query.one()
            except NoResultFound:
                if rep:
                    filters += [DataObject.id != 0]
                    continue
                raise CollectionDoesNotExist()
            return iRODSCollection(self, result)


    def create(self, path, recurse=True, **options):
        path = iRODSCollection.normalize_path( path )
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

    def touch(self, path, **options):
        """Change the mtime of an existing collection.

        Parameters
        ----------
        path: string
            The absolute logical path of a collection.

        seconds_since_epoch: integer, optional
            The number of seconds since epoch representing the new mtime. Cannot
            be used with "reference" parameter.

        reference: string, optional
            Use the mtime of the logical path to the data object or collection
            identified by this option. Cannot be used with "seconds_since_epoch"
            parameter.

        Raises
        ------
        CollectionDoesNotExist
            If the target collection does not exist or does not point to a
            collection.
        """
        # Attempt to lookup the collection. If it does not exist, the call
        # will raise an exception.
        #
        # Enforces the requirement that collections must exist before this
        # operation is invoked.
        self.get(path)

        # The following options to the touch API are not allowed for collections.
        options.pop('no_create', None)
        options.pop('replica_number', None)
        options.pop('leaf_resource_name', None)

        _api_impl._touch_impl(self.sess, path, no_create=True, **options)
