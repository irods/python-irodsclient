from __future__ import absolute_import
from os.path import basename, dirname
from os import O_RDONLY, O_WRONLY, O_RDWR, O_CREAT

from irods.models import DataObject
from irods.manager import Manager
from irods.message import (
    iRODSMessage, FileOpenRequest, ObjCopyRequest, StringStringMap)
from irods.exception import DataObjectDoesNotExist
from irods.api_number import api_number
from irods.data_object import iRODSDataObject, iRODSDataObjectFileRaw
from io import BufferedRandom
import irods.keywords as kw

SEEK_SET = 0
SEEK_CUR = 1
SEEK_END = 2


class DataObjectManager(Manager):

    def get(self, path):
        parent = self.sess.collections.get(dirname(path))

        query = self.sess.query(DataObject)\
            .filter(DataObject.name == basename(path))\
            .filter(DataObject.collection_id == parent.id)
        results = query.all()
        if len(results) <= 0:
            raise DataObjectDoesNotExist()
        return iRODSDataObject(self, parent, results)

    def create(self, path, resource=None, options=None):
        if options is None:
            options = {}
        kvp = {kw.DATA_TYPE_KW: 'generic'}
        if resource:
            kvp[kw.DEST_RESC_NAME_KW] = resource
        kvp.update(options)
        message_body = FileOpenRequest(
            objPath=path,
            createMode=0o644,
            openFlags=0,
            offset=0,
            dataSize=-1,
            numThreads=self.sess.numThreads,
            oprType=0,
            KeyValPair_PI=StringStringMap(kvp),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_CREATE_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
            desc = response.int_info
            conn.close_file(desc)

        return self.get(path)

    def open(self, path, mode, options=None):
        if options is None:
            options = {}

        flags, seek_to_end = {
            'r': (O_RDONLY, False),
            'r+': (O_RDWR, False),
            'w': (O_WRONLY | O_CREAT, False),
            'w+': (O_RDWR | O_CREAT, False),
            'a': (O_WRONLY | O_CREAT, True),
            'a+': (O_RDWR | O_CREAT, True),
        }[mode]
        # TODO: Use seek_to_end

        try:
            oprType = options[kw.OPR_TYPE_KW]
        except KeyError:
            oprType = 0

        # sanitize options before packing
        options = {str(key): str(value) for key, value in options.items()}

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

        return BufferedRandom(iRODSDataObjectFileRaw(conn, desc, options))

    def unlink(self, path, force=False, options=None):
        if options is None:
            options = {}
        if force:
            options[kw.FORCE_FLAG_KW] = ''
        message_body = FileOpenRequest(
            objPath=path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=-1,
            numThreads=self.sess.numThreads,
            oprType=0,
            KeyValPair_PI=StringStringMap(options),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_UNLINK_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()

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

    def copy(self, src_path, dest_path, options=None):
        if options is None:
            options = {}

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


    def truncate(self, path, size):
        options = {}
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

    def replicate(self, path, options=None):
        if options is None:
            options = {}
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
