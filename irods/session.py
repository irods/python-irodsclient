from __future__ import absolute_import
from irods.query import Query
from irods.pool import Pool
from irods.account import iRODSAccount
from irods.manager.collection_manager import CollectionManager
from irods.manager.data_object_manager import DataObjectManager
from irods.manager.metadata_manager import MetadataManager
from irods.manager.access_manager import AccessManager
from irods.manager.user_manager import UserManager, UserGroupManager
from irods.manager.resource_manager import ResourceManager
from irods.exception import NetworkException


class iRODSSession(object):

    def __init__(self, *args, **kwargs):
        self.pool = None
        if args or kwargs:
            self.configure(*args, **kwargs)

        self.collections = CollectionManager(self)
        self.data_objects = DataObjectManager(self)
        self.metadata = MetadataManager(self)
        self.permissions = AccessManager(self)
        self.users = UserManager(self)
        self.user_groups = UserGroupManager(self)
        self.resources = ResourceManager(self)
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()

    def cleanup(self):
        for conn in self.pool.active | self.pool.idle:
            try:
                conn.disconnect()
            except NetworkException:
                pass
            conn.release(True)

    def configure(self,
                  host=None, port=1247, user=None, zone=None,
                  password=None, client_user=None, client_zone=None,
                  server_dn=None, authentication_scheme='password'):
        account = iRODSAccount(host, int(port), user, zone, authentication_scheme, password, client_user, server_dn, client_zone)
        self.pool = Pool(account)

    def query(self, *args):
        return Query(self, *args)

        # WHY IS THIS HERE?
        # self.host = host
        # self.port = port
        # self.proxy_user = self.client_user = user
        # self.proxy_zone = self.client_zone = zone
    
                    
    @property
    def username(self):
        return self.pool.account.client_user

    @property
    def zone(self):
        return self.pool.account.client_zone

    @property
    def host(self):
        return self.pool.account.host

    @property
    def port(self):
        return self.pool.account.port
