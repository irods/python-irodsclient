from irods.query import Query
from irods.pool import Pool
from irods.account import iRODSAccount
from irods.resource_manager.collection_manager import CollectionManager
from irods.resource_manager.data_object_manager import DataObjectManager
from irods.resource_manager.metadata_manager import MetadataManager

class iRODSSession(object):
    def __init__(self, *args, **kwargs):
        self.pool = None
        if args or kwargs:
            self.configure(*args, **kwargs)
        self.collections = CollectionManager(self)
        self.data_objects = DataObjectManager(self)
        self.metadata = MetadataManager(self)
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()
        
    def cleanup(self):
        for conn in self.pool.active | self.pool.idle:
            conn.disconnect()
            conn.release(True)

    def configure(self, host=None, port=1247, user=None, zone=None, 
        password=None, client_user=None, client_zone=None):
        account = iRODSAccount(host, int(port), user, zone, password, client_user, 
            client_zone)
        self.pool = Pool(account)

    def query(self, *args):
        return Query(self, *args)
