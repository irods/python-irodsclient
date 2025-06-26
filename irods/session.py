import ast
import atexit
import copy
import errno
import json
import logging
from numbers import Number
import os
import threading
import weakref
import irods.auth
from irods.query import Query
from irods.genquery2 import GenQuery2
from irods.pool import Pool
from irods.account import iRODSAccount
from irods.api_number import api_number
import irods.client_configuration as client_config
from irods.manager.collection_manager import CollectionManager
from irods.manager.data_object_manager import DataObjectManager
from irods.manager.metadata_manager import MetadataManager
from irods.manager.access_manager import AccessManager
from irods.manager.user_manager import UserManager, GroupManager
from irods.manager.resource_manager import ResourceManager
from irods.manager.zone_manager import ZoneManager
from irods.message import iRODSMessage, STR_PI
from irods.exception import NetworkException, NotImplementedInIRODSServer
from irods.password_obfuscation import decode
from irods import NATIVE_AUTH_SCHEME, PAM_AUTH_SCHEMES
from . import at_client_exit
from . import DEFAULT_CONNECTION_TIMEOUT, MAXIMUM_CONNECTION_TIMEOUT

_fds = None
_fds_lock = threading.Lock()
_sessions = None
_sessions_lock = threading.Lock()


def _cleanup_remaining_sessions():
    for fd in list((_fds or {}).keys()):
        if not fd.closed:
            fd.close()
        # remove refs to session objects no longer needed
        fd._iRODS_session = None
    for ses in (_sessions or []).copy():
        ses.cleanup()  # internally modifies _sessions


with _sessions_lock:
    at_client_exit._register(
        at_client_exit.LibraryCleanupStage.DURING, _cleanup_remaining_sessions
    )


def _weakly_reference(ses):
    global _sessions, _fds
    try:
        if _sessions is None:
            with _sessions_lock:
                do_register = _sessions is None
                if do_register:
                    _sessions = weakref.WeakKeyDictionary()
                    _fds = weakref.WeakKeyDictionary()
    finally:
        _sessions[ses] = None


logger = logging.getLogger(__name__)


class NonAnonymousLoginWithoutPassword(RuntimeError):
    pass


class iRODSSession:

    def library_features(self):
        irods_version_needed = (4, 3, 1)
        if self.server_version < irods_version_needed:
            raise NotImplementedInIRODSServer("library_features", irods_version_needed)
        message = iRODSMessage(
            "RODS_API_REQ", int_info=api_number["GET_LIBRARY_FEATURES_AN"]
        )
        with self.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
            msg = response.get_main_message(STR_PI)
            return json.loads(msg.myStr)

    @property
    def env_file(self):
        return self._env_file

    @property
    def auth_file(self):
        return self._auth_file

    @property
    def available_permissions(self):
        from irods.access import iRODSAccess, _iRODSAccess_pre_4_3_0

        try:
            self.__access
        except AttributeError:
            self.__access = (
                _iRODSAccess_pre_4_3_0 if self.server_version < (4, 3) else iRODSAccess
            )
        return self.__access

    def __init__(self, configure=True, auto_cleanup=True, **kwargs):
        self.pool = None
        self.numThreads = 0
        self._env_file = ""
        self._auth_file = ""
        self.do_configure = kwargs if configure else {}
        self._cached_connection_timeout = None
        self.connection_timeout = kwargs.pop(
            "connection_timeout", DEFAULT_CONNECTION_TIMEOUT
        )
        self.__configured = None
        if configure:
            self.__configured = self.configure(**kwargs)

        self.collections = CollectionManager(self)
        self.data_objects = DataObjectManager(self)
        self.metadata = MetadataManager(self)
        self.acls = AccessManager(self)
        self.users = UserManager(self)
        self.groups = GroupManager(self)
        self.resources = ResourceManager(self)
        self.zones = ZoneManager(self)
        self._auto_cleanup = auto_cleanup
        self.ticket__ = ""
        # A mapping for each connection - holds whether the session's assigned ticket has been applied.
        self.ticket_applied = weakref.WeakKeyDictionary()

        self.auth_options_by_scheme = {
            "pam_password": {
                irods.auth.CLIENT_GET_REQUEST_RESULT: (lambda sess, conn: [])
            }
        }

        if auto_cleanup:
            _weakly_reference(self)

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

    def resolve_auth_options(self, scheme, conn):
        for key, value in self.auth_options_by_scheme.setdefault(scheme, {}).items():
            if callable(value):
                value = value(self, conn)
            conn.auth_options[key] = value

    def set_auth_option_for_scheme(self, scheme, key, value_or_factory_function):
        entry = self.auth_options_by_scheme.setdefault(scheme, {})
        old_key = entry.get(key)
        entry[key] = value_or_factory_function
        return old_key

    def clone(self, **kwargs):
        other = copy.copy(self)
        other.pool = None
        for k, v in vars(self).items():
            if getattr(v, "_set_manager_session", None) is not None:
                vcopy = copy.copy(v)
                # Deep-copy into the manager object for the cloned session and set its parent session
                # reference to correspond to the clone.
                setattr(other, k, vcopy)
                vcopy._set_manager_session(other)
            elif isinstance(v, iRODSAccount):
                # Deep-copy the iRODSAccount subobject, since we might be setting the hostname on that object.
                setattr(other, k, copy.copy(v))

        other.cleanup(new_host=kwargs.pop("host", ""))
        other.ticket__ = kwargs.pop("ticket", self.ticket__)
        other.ticket_applied = weakref.WeakKeyDictionary()
        if other._auto_cleanup:
            _weakly_reference(other)
        return other

    def cleanup(self, new_host=""):
        if self.pool:
            for conn in self.pool.active | self.pool.idle:
                try:
                    conn.disconnect()
                except NetworkException:
                    pass
                conn.release(True)
        if self.do_configure:
            if new_host:
                d = self.do_configure.setdefault("_overrides", {})
                d["irods_host"] = new_host
                self.__configured = None
            self.__configured = self.configure(**self.do_configure)

    def _configure_account(self, **kwargs):
        env_file = None
        try:
            env_file = kwargs["irods_env_file"]
        except KeyError:
            # For backward compatibility
            for key in ["host", "port", "authentication_scheme"]:
                if key in kwargs:
                    kwargs["irods_{}".format(key)] = kwargs.pop(key)

            for key in ["user", "zone"]:
                if key in kwargs:
                    kwargs["irods_{}_name".format(key)] = kwargs.pop(key)

            return iRODSAccount(**kwargs)

        # Get credentials from irods environment file
        creds = self.get_irods_env(env_file, session_=self)

        # Update with new keywords arguments only
        creds.update((key, value) for key, value in kwargs.items() if key not in creds)

        if env_file:
            creds["env_file"] = env_file

        # Get auth scheme
        try:
            auth_scheme = creds["irods_authentication_scheme"]
        except KeyError:
            # default
            auth_scheme = "native"

        if auth_scheme.lower() in PAM_AUTH_SCHEMES:
            # inline password
            if "password" in creds:
                return iRODSAccount(**creds)
            else:
                # password will be from irodsA file therefore use native login
                # but let PAM still be recorded as the original scheme
                creds["irods_authentication_scheme"] = (NATIVE_AUTH_SCHEME, auth_scheme)
        elif auth_scheme != "native":
            return iRODSAccount(**creds)

        # Native auth, try to unscramble password
        try:
            creds["irods_authentication_uid"] = kwargs["irods_authentication_uid"]
        except KeyError:
            pass

        missing_file_path = []
        error_args = []
        pw = creds["password"] = self.get_irods_password(
            session_=self, file_path_if_not_found=missing_file_path, **creds
        )
        # For native authentication, a missing password should be flagged as an error for non-anonymous logins.
        # However, the pam_password case has its own internal checks.
        if auth_scheme.lower() not in PAM_AUTH_SCHEMES:
            if not pw and creds.get("irods_user_name") != "anonymous":
                if missing_file_path:
                    error_args += [
                        "Authentication file not found at {!r}".format(
                            missing_file_path[0]
                        )
                    ]
                raise NonAnonymousLoginWithoutPassword(*error_args)

        return iRODSAccount(**creds)

    def configure(self, **kwargs):
        account = self.__configured
        if not account:
            account = self._configure_account(**kwargs)
        # so that _login_pam can rewrite auth file with new password if requested:
        account._auth_file = getattr(self, "_auth_file", "")
        connection_refresh_time = self.get_connection_refresh_time(**kwargs)
        logger.debug(
            "In iRODSSession's configure(). connection_refresh_time set to {}".format(
                connection_refresh_time
            )
        )
        self.pool = Pool(
            account,
            application_name=kwargs.pop("application_name", ""),
            connection_refresh_time=connection_refresh_time,
            session=self,
        )
        conn_timeout = getattr(self, "_cached_connection_timeout", None)
        self.pool.connection_timeout = conn_timeout
        return account

    def query(self, *args, **kwargs):
        return Query(self, *args, **kwargs)

    def genquery2_object(self, **kwargs):
        """Returns GenQuery2 object

        Returns GenQuery2 object that can be used to execute GenQuery2 queries,
        to retrieve the SQL query for a particular GenQuery2 query, and to
        get GenQuery2 column mappings.
        """
        return GenQuery2(self, **kwargs)

    def genquery2(self, query, **kwargs):
        """Shorthand for executing a single GenQuery2 query."""
        q = GenQuery2(self)
        return q.execute(query, **kwargs)

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
        return self._server_version()

    def server_version_without_auth(self):
        """Returns the same version tuple as iRODSSession's server_version property, but
        does not require successful authentication.
        """
        from irods.connection import Connection

        with self.clone().pool.no_auto_authenticate() as pool:
            return Connection(pool, pool.account).server_version

    GET_SERVER_VERSION_WITHOUT_AUTH = staticmethod(
        lambda s: s.server_version_without_auth()
    )

    def _server_version(self, version_func=None):
        """The server version can be retrieved by the usage:

            session._server_version()

        with conditional substitution by another version by use of the environment variable:

            PYTHON_IRODSCLIENT_REPORTED_SERVER_VERSION.

        Also: if iRODSServer.GET_SERVER_VERSION_WITHOUT_AUTH is passed in version_func, the true server
        version can be accessed without first going through authentication.
        Example:
            ses = irods.helpers.make_session()
            vsn = ses._server_version( ses.GET_SERVER_VERSION_WITHOUT_AUTH )
        """
        reported_vsn = os.environ.get("PYTHON_IRODSCLIENT_REPORTED_SERVER_VERSION", "")
        if reported_vsn:
            return tuple(ast.literal_eval(reported_vsn))
        return self.__server_version() if version_func is None else version_func(self)

    def __server_version(self):
        try:
            conn = next(iter(self.pool.active))
            return conn.server_version
        except StopIteration:
            conn = self.pool.get_connection()
            version = conn.server_version
            conn.release()
            return version

    @property
    def client_hints(self):
        message = iRODSMessage("RODS_API_REQ", int_info=api_number["CLIENT_HINTS_AN"])
        with self.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
        return response.get_json_encoded_struct()

    @property
    def pam_pw_negotiated(self):
        old_setting = _dummy = object()
        try:
            self.pool.account.store_pw = box = []
            if (
                self.server_version_without_auth() >= (4, 3)
                and not client_config.legacy_auth.force_legacy_auth
            ):
                old_setting = self.set_auth_option_for_scheme(
                    "pam_password", irods.auth.CLIENT_GET_REQUEST_RESULT, box
                )
            conn = self.pool.get_connection()
            pw = getattr(self.pool.account, "store_pw", [])
            delattr(self.pool.account, "store_pw")
            conn.release()
            return pw
        finally:
            if old_setting is not _dummy:
                self.set_auth_option_for_scheme(
                    "pam_password", irods.auth.CLIENT_GET_REQUEST_RESULT, old_setting
                )

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
        if seconds == 0:
            exc = ValueError(
                "Setting an iRODS connection_timeout to 0 seconds would make it non-blocking."
            )
            raise exc
        elif isinstance(seconds, Number):
            # Note: We can handle infinities because -Inf < 0 and Inf > MAXIMUM_CONNECTION_TIMEOUT.
            if seconds < 0 or str(seconds) == "nan":
                exc = ValueError(
                    "The iRODS connection_timeout may not be assigned a negative, out-of-bounds, or otherwise rogue value (eg: NaN, -Inf)."
                )
                raise exc
            elif seconds > MAXIMUM_CONNECTION_TIMEOUT:
                logging.getLogger(__name__).warning(
                    "Hard limiting connection timeout of %g to the maximum allowable value of %g",
                    seconds,
                    MAXIMUM_CONNECTION_TIMEOUT,
                )
                seconds = MAXIMUM_CONNECTION_TIMEOUT
        elif seconds is None:
            pass
        else:
            exc = ValueError(
                "The iRODS connection_timeout must be assigned a positive int, positive float, or None."
            )
            raise exc
        self._cached_connection_timeout = seconds
        if self.pool:
            self.pool.connection_timeout = seconds

    @staticmethod
    def get_irods_password_file():
        try:
            return os.environ["IRODS_AUTHENTICATION_FILE"]
        except KeyError:
            return os.path.expanduser("~/.irods/.irodsA")

    @staticmethod
    def get_irods_env(env_file, session_=None):
        try:
            with open(env_file, "rt") as f:
                j = json.load(f)
                if session_ is not None:
                    session_._env_file = env_file
                return j
        except IOError:
            logger.debug("Could not open file {}".format(env_file))
            return {}

    @staticmethod
    def get_irods_password(session_=None, file_path_if_not_found=(), **kwargs):
        path_memo = []
        try:
            irods_auth_file = kwargs["irods_authentication_file"]
        except KeyError:
            irods_auth_file = iRODSSession.get_irods_password_file()

        try:
            uid = kwargs["irods_authentication_uid"]
        except KeyError:
            uid = None

        _retval = ""

        try:
            with open(irods_auth_file, "r") as f:
                _retval = decode(f.read().rstrip("\n"), uid)
                return _retval
        except IOError as exc:
            if exc.errno != errno.ENOENT:
                raise  # Auth file exists but can't be read
            path_memo = [irods_auth_file]
            return ""  # No auth file (as with anonymous user)
        finally:
            if isinstance(file_path_if_not_found, list) and path_memo:
                file_path_if_not_found[:] = path_memo
            if session_ is not None and _retval:
                session_._auth_file = irods_auth_file

    def get_connection_refresh_time(self, **kwargs):
        connection_refresh_time = -1

        connection_refresh_time = int(kwargs.get("refresh_time", -1))
        if connection_refresh_time != -1:
            return connection_refresh_time

        try:
            env_file = kwargs["irods_env_file"]
        except KeyError:
            return connection_refresh_time

        if env_file is not None:
            env_file_map = self.get_irods_env(env_file)
            connection_refresh_time = int(
                env_file_map.get("irods_connection_refresh_time", -1)
            )
            if connection_refresh_time < 1:
                # Negative values are not allowed.
                logger.debug(
                    "connection_refresh_time in {} file has value of {}. Only values greater than 1 are allowed.".format(
                        env_file, connection_refresh_time
                    )
                )
                connection_refresh_time = -1

        return connection_refresh_time
