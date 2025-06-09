import importlib
import logging
import weakref
from irods.api_number import api_number
from irods.message import iRODSMessage, JSON_Message
import irods.password_obfuscation as obf
import irods.session


__all__ = ["pam_interactive", "pam_password", "native"]


AUTH_PLUGIN_PACKAGE = "irods.auth"


# Python3 does not have types.NoneType
_NoneType = type(None)


class AuthStorage:
    """A class that facilitates flexible means of password storage.

    Using an instance of this class, passwords may either be one of the following:

        - directly placed in a member attribute (pw), or

        - they may be written to / read from a specified file path in encoded
          form, usually in an .irodsA file intended for iRODS client authentication.

    Most typical of this class's utility is the transfer of password information from
    the pam_password to the native authentication flow.  In this usage, whether the
    password is stored in RAM or in the filesystem depends on whether it was read
    originally as a function parameter or from an authentication file, respectively,
    when the session was created.
    """

    @staticmethod
    def get_env_password(filename=None):
        options = dict(irods_authentication_file=filename) if filename else {}
        return irods.session.iRODSSession.get_irods_password(**options)

    @staticmethod
    def get_env_password_file():
        return irods.session.iRODSSession.get_irods_password_file()

    @staticmethod
    def set_env_password(unencoded_pw, filename=None):
        if filename is None:
            filename = AuthStorage.get_env_password_file()
        from ..client_init import _open_file_for_protected_contents

        with _open_file_for_protected_contents(filename, "w") as irodsA:
            irodsA.write(obf.encode(unencoded_pw))
        return filename

    @staticmethod
    def get_temp_pw_storage(conn):
        """Fetch the AuthStorage instance associated with this connection object."""
        return getattr(conn, "auth_storage", lambda: None)()

    @staticmethod
    def create_temp_pw_storage(conn):
        """Creates an AuthStorage instance to be cached and associated with this connection object.

        Called multiple times for the same connection, it will return the cached instance.

        The value returned by this call should be stored by the caller into an appropriately scoped
        variable to ensure the AuthStorage instance endures for the desired lifetime -- that is,
        for however long we wish to keep the password information around.  This is because the
        connection object only maintains a weak reference to said instance.
        """

        # resolve the weakly referenced AuthStorage obj for the connection if there is one.
        weakref_to_store = getattr(conn, "auth_storage", None)
        store = weakref_to_store and weakref_to_store()

        # In absence of a persistent AuthStorage object, create one.
        if store is None:
            store = AuthStorage(conn)
            # So that the connection object doesn't hold on to password data too long:
            conn.auth_storage = weakref.ref(store)
        return store

    def __init__(self, conn):
        self.conn = conn
        self.pw = ""
        self._auth_file = ""

    @property
    def auth_file(self):
        if self._auth_file is None:
            return ""
        return self._auth_file or self.conn.account.derived_auth_file

    def use_client_auth_file(self, auth_file):
        """Set to None to completely suppress use of an .irodsA auth file."""
        if isinstance(auth_file, (str, _NoneType)):
            self._auth_file = auth_file
        else:
            msg = f"Invalid object in {self.__class__}._auth_file"
            raise RuntimeError(msg)

    def store_pw(self, pw):
        if self.auth_file:
            self.set_env_password(pw, filename=self.auth_file)
        else:
            self.pw = pw

    def retrieve_pw(self):
        if self.auth_file:
            return self.get_env_password(filename=self.auth_file)
        return self.pw


def load_plugins(subset=set(), _reload=False):
    if not subset:
        subset = set(__all__)
    dir_ = set(globals()) & set(__all__)  # plugins already loaded
    for s in subset:
        if s not in dir_ or _reload:
            mod = importlib.import_module("." + s, package=AUTH_PLUGIN_PACKAGE)
            if _reload:
                importlib.reload(mod)
        dir_ |= {s}
    return dir_


class REQUEST_IS_MISSING_KEY(Exception):
    pass


class ClientAuthError(Exception):
    pass


def throw_if_request_message_is_missing_key(request, required_keys):
    for key in required_keys:
        if not key in request:
            raise REQUEST_IS_MISSING_KEY(f"key = {key}")


def _auth_api_request(conn, data):
    message_body = JSON_Message(data, conn.server_version)
    message = iRODSMessage(
        "RODS_API_REQ", msg=message_body, int_info=api_number["AUTHENTICATION_APN"]
    )
    conn.send(message)
    response = conn.recv()
    return response.get_json_encoded_struct()


__FLOW_COMPLETE__ = "authentication_flow_complete"
__NEXT_OPERATION__ = "next_operation"


CLIENT_GET_REQUEST_RESULT = "client_get_request_result"
FORCE_PASSWORD_PROMPT = "force_password_prompt"
STORE_PASSWORD_IN_MEMORY = "store_password_in_memory"


class authentication_base:

    def __init__(self, connection, scheme):
        self.conn = connection
        self.loggedIn = 0
        self.scheme = scheme

    def call(self, next_operation, request):
        logging.debug("next operation = %r", next_operation)
        old_func = func = next_operation
        # One level of indirection should be sufficient to get a callable method.
        if not callable(func):
            old_func, func = (func, getattr(self, func, None))
        func = func or old_func
        if not callable(func):
            raise RuntimeError("client request contains no callable 'next_operation'")
        resp = func(request)
        logging.debug("resp = %r", resp)
        return resp

    def authenticate_client(
        self, next_operation="auth_client_start", initial_request=()
    ):
        if not isinstance(initial_request, dict):
            initial_request = dict(initial_request)

        to_send = initial_request.copy()
        to_send["scheme"] = self.scheme

        while True:
            resp = self.call(next_operation, to_send)
            if self.loggedIn:
                break
            next_operation = resp.get(__NEXT_OPERATION__)
            if next_operation is None:
                raise ClientAuthError(
                    "next_operation key missing; cannot determine next operation"
                )
            if next_operation in (__FLOW_COMPLETE__, ""):
                raise ClientAuthError(
                    f"authentication flow stopped without success: scheme = {self.scheme}"
                )
            to_send = resp

        logging.debug("fully authenticated")
