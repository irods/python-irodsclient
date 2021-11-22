from __future__ import absolute_import
import os
import json
import errno
import logging
from irods.query import Query
from irods.pool import Pool
from irods.account import iRODSAccount
from irods.manager.collection_manager import CollectionManager
from irods.manager.data_object_manager import DataObjectManager
from irods.manager.metadata_manager import MetadataManager
from irods.manager.access_manager import AccessManager
from irods.manager.user_manager import UserManager, UserGroupManager
from irods.manager.resource_manager import ResourceManager
from irods.manager.zone_manager import ZoneManager
from irods.exception import NetworkException
from irods.password_obfuscation import decode
from irods import NATIVE_AUTH_SCHEME, PAM_AUTH_SCHEME

logger = logging.getLogger(__name__)

class NonAnonymousLoginWithoutPassword(RuntimeError): pass

class iRODSSession(object):

    @property
    def env_file (self):
        return self._env_file

    @property
    def auth_file (self):
        return self._auth_file

    def __init__(self, configure=True, **kwargs):
        self.pool = None
        self.numThreads = 0
        self._env_file = ''
        self._auth_file = ''
        self.do_configure = (kwargs if configure else {})
        self.__configured = None
        if configure:
            self.__configured = self.configure(**kwargs)

        self.collections = CollectionManager(self)
        self.data_objects = DataObjectManager(self)
        self.metadata = MetadataManager(self)
        self.permissions = AccessManager(self)
        self.users = UserManager(self)
        self.user_groups = UserGroupManager(self)
        self.resources = ResourceManager(self)
        self.zones = ZoneManager(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()

    def __del__(self):
        self.do_configure = {}
        # If self.pool has been fully initialized (ie. no exception was
        #   raised during __init__), then try to clean up.
        if self.pool is not None:
            self.cleanup()

    def cleanup(self):
        for conn in self.pool.active | self.pool.idle:
            try:
                conn.disconnect()
            except NetworkException:
                pass
            conn.release(True)
        if self.do_configure: 
            self.__configured = self.configure(**self.do_configure)

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
        creds = self.get_irods_env(env_file, session_ = self)

        # Update with new keywords arguments only
        creds.update((key, value) for key, value in kwargs.items() if key not in creds)

        # Get auth scheme
        try:
            auth_scheme = creds['irods_authentication_scheme']
        except KeyError:
            # default
            auth_scheme = 'native'

        if auth_scheme.lower() == PAM_AUTH_SCHEME:
            if 'password' in creds:
                return iRODSAccount(**creds)
            else:
                # password will be from irodsA file therefore use native login
                creds['irods_authentication_scheme'] = NATIVE_AUTH_SCHEME
        elif auth_scheme != 'native':
            return iRODSAccount(**creds)

        # Native auth, try to unscramble password
        try:
            creds['irods_authentication_uid'] = kwargs['irods_authentication_uid']
        except KeyError:
            pass

        missing_file_path = []
        error_args = []
        pw = creds['password'] = self.get_irods_password(session_ = self, file_path_if_not_found = missing_file_path, **creds)
        if not pw and creds.get('irods_user_name') != 'anonymous':
            if missing_file_path:
                error_args += ["Authentication file not found at {!r}".format(missing_file_path[0])]
            raise NonAnonymousLoginWithoutPassword(*error_args)

        return iRODSAccount(**creds)

    def configure(self, **kwargs):
        account = self.__configured
        if not account:
            account = self._configure_account(**kwargs)
        connection_refresh_time = self.get_connection_refresh_time(**kwargs)
        logger.debug("In iRODSSession's configure(). connection_refresh_time set to {}".format(connection_refresh_time))
        self.pool = Pool(account, application_name=kwargs.pop('application_name',''), connection_refresh_time=connection_refresh_time)
        return account

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
    def pam_pw_negotiated(self):
            self.pool.account.store_pw = []
            conn = self.pool.get_connection()
            pw = getattr(self.pool.account,'store_pw',[])
            delattr( self.pool.account, 'store_pw')
            conn.release()
            return pw

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
    def get_irods_env(env_file, session_ = None):
        try:
            with open(env_file, 'rt') as f:
                j = json.load(f)
                if session_ is not None:
                    session_._env_file = env_file
                return j
        except IOError:
            logger.debug("Could not open file {}".format(env_file))
            return {}

    @staticmethod
    def get_irods_password(session_ = None, file_path_if_not_found = (), **kwargs):
        path_memo  = []
        try:
            irods_auth_file = kwargs['irods_authentication_file']
        except KeyError:
            irods_auth_file = iRODSSession.get_irods_password_file()

        try:
            uid = kwargs['irods_authentication_uid']
        except KeyError:
            uid = None

        _retval = ''

        try:
            with open(irods_auth_file, 'r') as f:
                _retval = decode(f.read().rstrip('\n'), uid)
                return _retval
        except IOError as exc:
            if exc.errno != errno.ENOENT:
                raise  # Auth file exists but can't be read
            path_memo = [ irods_auth_file ]
            return ''                           # No auth file (as with anonymous user)
        finally:
            if isinstance(file_path_if_not_found, list) and path_memo:
                file_path_if_not_found[:] = path_memo
            if session_ is not None and _retval:
                session_._auth_file = irods_auth_file

    def get_connection_refresh_time(self, **kwargs):
        connection_refresh_time = -1
        
        connection_refresh_time = int(kwargs.get('refresh_time', -1))
        if connection_refresh_time != -1:
            return connection_refresh_time

        try:
            env_file = kwargs['irods_env_file']
        except KeyError:
            return connection_refresh_time

        if env_file is not None:
            env_file_map = self.get_irods_env(env_file)
            connection_refresh_time = int(env_file_map.get('irods_connection_refresh_time', -1))
            if connection_refresh_time < 1:
                # Negative values are not allowed.
                logger.debug('connection_refresh_time in {} file has value of {}. Only values greater than 1 are allowed.'.format(env_file, connection_refresh_time))
                connection_refresh_time = -1

        return connection_refresh_time
