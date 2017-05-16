from __future__ import absolute_import
import os
import json
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
from irods.password_obfuscation import decode


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
                  server_dn=None, authentication_scheme='password',
                  irods_env_file=None, numThreads=0):

        if irods_env_file:
            creds = self.get_irods_env(irods_env_file)
            creds['password']=self.get_irods_auth(creds)
            account = iRODSAccount(**creds)
        else:
            account = iRODSAccount(
                host, int(port), user, zone, authentication_scheme,
                password, client_user, server_dn, client_zone)

        self.pool = Pool(account)
        self.numThreads = numThreads

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

    @staticmethod
    def get_irods_env(env_file):
        with open(env_file, 'rt') as f:
            return json.load(f)

    @staticmethod
    def get_irods_auth(env):
        try:
            irods_auth_file = env['irods_authentication_file']
        except KeyError:
            irods_auth_file = os.path.expanduser('~/.irods/.irodsA')

        with open(irods_auth_file, 'r') as f:
            return decode(f.read().rstrip('\n'))
