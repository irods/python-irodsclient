import logging

from query import Query
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
