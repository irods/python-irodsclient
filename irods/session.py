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

    def __init__(self, configure=True, **kwargs):
        self.pool = None
        self.numThreads = 0

        if configure:
            self.configure(**kwargs)

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

    def _configure_account(self, **kwargs):
        try:
            env_file = kwargs['irods_env_file']

        except KeyError:
            # For backward compatibility
            for key in ['host', 'port', 'authentication_scheme']:
                if key in kwargs:
                    kwargs['irods_{}'.format(key)] = kwargs.pop(key)

            for key in ['user', 'zone']:
                if key in kwargs:
                    kwargs['irods_{}_name'.format(key)] = kwargs.pop(key)

            return iRODSAccount(**kwargs)

        # Get credentials from irods environment file
        creds = self.get_irods_env(env_file)

        # Update with new keywords arguments only
        creds.update((key, value) for key, value in kwargs.items() if key not in creds)

        # Get auth scheme
        try:
            auth_scheme = creds['irods_authentication_scheme']
        except KeyError:
            # default
            auth_scheme = 'native'

        if auth_scheme != 'native':
            return iRODSAccount(**creds)

        # Native auth, try to unscramble password
        try:
            creds['irods_authentication_uid'] = kwargs['irods_authentication_uid']
        except KeyError:
            pass

        creds['password'] = self.get_irods_password(**creds)

        return iRODSAccount(**creds)


    def configure(self, **kwargs):
        account = self._configure_account(**kwargs)
        self.pool = Pool(account)

    def query(self, *args):
        return Query(self, *args)

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

    @property
    def server_version(self):
        try:
            conn = next(iter(self.pool.active))
            return conn.server_version
        except StopIteration:
            conn = self.pool.get_connection()
            version = conn.server_version
            conn.release()
            return version

    @property
    def default_resource(self):
        return self.pool.account.default_resource

    @default_resource.setter
    def default_resource(self, name):
        self.pool.account.default_resource = name

    @property
    def connection_timeout(self):
        return self.pool.connection_timeout

    @connection_timeout.setter
    def connection_timeout(self, seconds):
        self.pool.connection_timeout = seconds

    @staticmethod
    def get_irods_password_file():
        try:
            return os.environ['IRODS_AUTHENTICATION_FILE']
        except KeyError:
            return os.path.expanduser('~/.irods/.irodsA')

    @staticmethod
    def get_irods_env(env_file):
        with open(env_file, 'rt') as f:
            return json.load(f)

    @staticmethod
    def get_irods_password(**kwargs):
        try:
            irods_auth_file = kwargs['irods_authentication_file']
        except KeyError:
            irods_auth_file = iRODSSession.get_irods_password_file()

        try:
            uid = kwargs['irods_authentication_uid']
        except KeyError:
            uid = None

        with open(irods_auth_file, 'r') as f:
            return decode(f.read().rstrip('\n'), uid)
