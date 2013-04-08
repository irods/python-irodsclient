import socket 
import hashlib
import struct
import logging
from os.path import basename, dirname
from os import O_RDONLY, O_WRONLY, O_RDWR

from message import (iRODSMessage, StartupPack, authResponseInp, GenQueryOut, 
    DataObjInp, authRequestOut, KeyValPair, dataObjReadInp, dataObjWriteInp,
    fileLseekInp, fileLseekOut, dataObjCloseInp, ModAVUMetadataInp,
    empty_gen_query_out)
from query import Query
from exception import (get_exception_by_code, CAT_NO_ROWS_FOUND, 
    CollectionDoesNotExist, DataObjectDoesNotExist)
from results import ResultSet
from models import (Collection, DataObject, Resource, User, DataObjectMeta, 
    CollectionMeta, ResourceMeta, UserMeta)
from collection import iRODSCollection
from data_object import iRODSDataObject
from api_number import api_number
from meta import iRODSMeta
from pool import Pool
from account import iRODSAccount

class iRODSSession(object):
    def __init__(self, *args, **kwargs):
        self.pool = None
        if args or kwargs:
            self.configure(*args, **kwargs)

    def configure(self, host=None, port=1247, user=None, zone=None, password=None):
        account = iRODSAccount(host, port, user, zone, password)
        self.pool = Pool(account)

    def get_collection(self, path):
        query = self.query(Collection).filter(Collection.name == path)
        results = self.execute_query(query)
        # todo implement this with .one() on query
        if results.length == 1:
            return iRODSCollection(self, results[0])
        else:
            raise CollectionDoesNotExist()

    def get_data_object(self, path):
        try:
            parent = self.get_collection(dirname(path))
        except CollectionDoesNotExist:
            raise DataObjectDoesNotExist()

        results = self.query(DataObject)\
            .filter(DataObject.name == basename(path))\
            .filter(DataObject.collection_id == parent.id)\
            .all()
        if results.length == 1:
            return iRODSDataObject(self, parent, results[0])
        else:
            raise DataObjectDoesNotExist()

    def create_data_object(self, path):
        message_body = DataObjInp(
            objPath=path,
            createMode=0644,
            openFlags=0,
            offset=0,
            dataSize=-1,
            numThreads=0,
            oprType=0,
            KeyValPair_PI=KeyValPair({'dataType': 'generic'}),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
            int_info=api_number['DATA_OBJ_CREATE_AN'])

        with self.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()

        desc = response.int_info
        self.close_file(desc)
        return self.get_data_object(path)

    def open_file(self, path, mode):
        message_body = DataObjInp(
            objPath=path,
            createMode=0,
            openFlags=mode,
            offset=0,
            dataSize=-1,
            numThreads=0,
            oprType=0,
            KeyValPair_PI=KeyValPair(),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body, 
            int_info=api_number['DATA_OBJ_OPEN_AN'])

        conn = self.pool.get_connection()
        conn.send(message)
        response = conn.recv()
        return (conn, response.int_info)

    def unlink_data_object(self, path):
        message_body = DataObjInp(
            objPath=path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=-1,
            numThreads=0,
            oprType=0,
            KeyValPair_PI=KeyValPair(),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
            int_info=api_number['DATA_OBJ_UNLINK_AN'])

        with self.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()

    @staticmethod
    def _model_class_to_resource_type(model_cls):
        return {
            DataObject: 'd',
            Collection: 'c',
            Resource: 'r',
            User: 'r',
        }[model_cls]

    def get_meta(self, model_cls, path):
        resource_type = self._model_class_to_resource_type(model_cls)
        model = {
            'd': DataObjectMeta,
            'c': CollectionMeta,
            'r': ResourceMeta,
            'u': UserMeta
        }[resource_type]
        conditions = {
            'd': [
                Collection.name == dirname(path), 
                DataObject.name == basename(path)
            ],
            'c': [Collection.name == path],
            'r': [Resource.name == path],
            'u': [User.name == path]
        }[resource_type]
        results = self.query(model.id, model.name, model.value, model.units)\
            .filter(*conditions).all()
        return [iRODSMeta(
            row[model.name], 
            row[model.value], 
            row[model.units],
            id=row[model.id]
        ) for row in results]

    def add_meta(self, model_cls, path, meta):
        resource_type = self._model_class_to_resource_type(model_cls)
        message_body = ModAVUMetadataInp(
            "add",
            "-" + resource_type,
            path,
            meta.name,
            meta.value,
            meta.units
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body, 
            int_info=api_number['MOD_AVU_METADATA_AN'])
        with self.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logging.debug(response.int_info)

    def remove_meta(self, model_cls, path, meta):
        resource_type = self._model_class_to_resource_type(model_cls)
        message_body = ModAVUMetadataInp(
            "rm",
            "-" + resource_type,
            path,
            meta.name,
            meta.value,
            meta.units
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body, 
            int_info=api_number['MOD_AVU_METADATA_AN'])
        with self.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logging.debug(response.int_info)

    def copy_meta(self, src_model_cls, dest_model_cls, src, dest):
        src_resource_type = self._model_class_to_resource_type(src_model_cls)
        dest_resource_type = self._model_class_to_resource_type(dest_model_cls)
        message_body = ModAVUMetadataInp(
            "cp",
            "-" + src_resource_type,
            "-" + dest_resource_type,
            src,
            dest
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body, 
            int_info=api_number['MOD_AVU_METADATA_AN'])

        with self.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logging.debug(response.int_info)
        
    def query(self, *args):
        return Query(self, *args)

    def execute_query(self, query):
        message_body = query._message()
        message = iRODSMessage('RODS_API_REQ', msg=message_body, int_info=702)
        with self.pool.get_connection() as conn:
            conn.send(message)
            try:
                result_message = conn.recv()
                results = result_message.get_main_message(GenQueryOut)
                result_set = ResultSet(results)
            except CAT_NO_ROWS_FOUND:
                result_set = ResultSet(empty_gen_query_out(query.columns.keys())) 
        return result_set
