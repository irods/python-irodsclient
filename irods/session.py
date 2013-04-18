import socket 
import hashlib
import struct
import logging
from os.path import basename, dirname
from os import O_RDONLY, O_WRONLY, O_RDWR

from message import (iRODSMessage, StartupPack, AuthResponse, GenQueryResponse, 
    FileOpenRequest, AuthChallenge, StringStringMap, FileReadRequest, 
    FileWriteRequest, FileSeekRequest, FileSeekResponse, FileCloseRequest, 
    MetadataRequest, CollectionRequest, empty_gen_query_out)
from query import Query
from exception import (get_exception_by_code, CAT_NO_ROWS_FOUND, 
    CollectionDoesNotExist, DataObjectDoesNotExist)
from results import ResultSet
from models import (Collection, DataObject, Resource, User, DataObjectMeta, 
    CollectionMeta, ResourceMeta, UserMeta)
from collection import iRODSCollection, CollectionManager
from data_object import iRODSDataObject, DataObjectManager
from meta import iRODSMeta, MetadataManager
from api_number import api_number
from pool import Pool
from account import iRODSAccount

class iRODSSession(object):
    def __init__(self, *args, **kwargs):
        self.pool = None
        if args or kwargs:
            self.configure(*args, **kwargs)
        self.collections = CollectionManager(self)
        self.data_objects = DataObjectManager(self)
        self.metadata = MetadataManager(self)

    def configure(self, host=None, port=1247, user=None, zone=None, password=None):
        account = iRODSAccount(host, port, user, zone, password)
        self.pool = Pool(account)

    def query(self, *args):
        return Query(self, *args)

    def execute_query(self, query):
        message_body = query._message()
        message = iRODSMessage('RODS_API_REQ', msg=message_body, int_info=702)
        with self.pool.get_connection() as conn:
            conn.send(message)
            try:
                result_message = conn.recv()
                results = result_message.get_main_message(GenQueryResponse)
                result_set = ResultSet(results)
            except CAT_NO_ROWS_FOUND:
                result_set = ResultSet(empty_gen_query_out(query.columns.keys())) 
        return result_set
