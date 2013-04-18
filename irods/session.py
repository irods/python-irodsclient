import logging

from message import iRODSMessage, GenQueryResponse, empty_gen_query_out
from query import Query
from exception import CAT_NO_ROWS_FOUND
from results import ResultSet
from api_number import api_number
from pool import Pool
from account import iRODSAccount
from collection import CollectionManager
from data_object import DataObjectManager
from meta import MetadataManager

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
