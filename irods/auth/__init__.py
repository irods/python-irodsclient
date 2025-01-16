import logging
import weakref
from irods.api_number import api_number
from irods.message import iRODSMessage, JSON_Message
import irods.password_obfuscation as obf
import irods.session


__all__ = ["pam_password", "native"]


AUTH_PLUGIN_PACKAGE = "irods.auth"


import importlib


class AuthStorage:

    @staticmethod
    def get_env_password():
        return irods.session.iRODSSession.get_irods_password()

    @staticmethod
    def set_env_password(unencoded_pw):
        with open(irods.session.iRODSSession.get_irods_password_file(),'w') as irodsA:
            irodsA.write(obf.encode(unencoded_pw))

    @staticmethod
    def get_temp_pw_storage(conn):
        return getattr(conn,'auth_storage',lambda:None)()

    @staticmethod
    def create_temp_pw_storage(conn):
        """A reference to the value returned by this call should be stored for the duration of the
           authentication exchange.
        """
        store = getattr(conn,'auth_storage',None)
        if store is None:
            store = AuthStorage(conn)
            # So that the connection object doesn't hold on to password data too long:
            conn.auth_storage = weakref.ref(store)
        return store

    def __init__(self, conn):
        self.conn = conn
        self.pw = ''

    def store_pw(self,pw):
        if self.conn.account.env_file:
            self.set_env_password(pw)
        else:
            self.pw = pw

    def retrieve_pw(self):
        if self.conn.account.env_file:
            return self.get_env_password()
        return pw


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


class REQUEST_IS_MISSING_KEY(Exception): pass


def throw_if_request_message_is_missing_key( request, required_keys ):
  for key in required_keys:
    if not key in request:
      raise REQUEST_IS_MISSING_KEY(f"key = {key}")


def _auth_api_request(conn, data):
    message_body = JSON_Message(data, conn.server_version)
    message = iRODSMessage('RODS_API_REQ', msg=message_body,
        int_info=api_number['AUTHENTICATION_APN']
    )
    conn.send(message)
    response = conn.recv()
    return response.get_json_encoded_struct()


__FLOW_COMPLETE__ = "authentication_flow_complete"
__NEXT_OPERATION__ = "next_operation"


class authentication_base:

    def __init__(self, connection, scheme):
        self.conn = connection
        self.loggedIn = 0
        self.scheme = scheme

    def call(self, next_operation, request):
        logging.info('next operation = %r', next_operation)
        old_func = func = next_operation
        while isinstance(func, str):
            old_func, func = (func, getattr(self, func, None))
        func = (func or old_func)
        if not func:
            raise RuntimeError("client request contains no callable 'next_operation'")
        resp = func(request)
        logging.info('resp = %r',resp)
        return resp

    def authenticate_client(self, next_operation = "auth_client_start", initial_request = {}):

        to_send = initial_request.copy()
        to_send["scheme"] = self.scheme

        while True:
            resp = self.call(next_operation, to_send)
            if self.loggedIn:
                break
            next_operation = resp.get(__NEXT_OPERATION__)
            if next_operation is None:
              raise ClientAuthError("next_operation key missing; cannot determine next operation")
            if next_operation in (__FLOW_COMPLETE__,""):
              raise ClientAuthError(f"authentication flow stopped without success: scheme = {self.scheme}")
            to_send = resp

        logging.info("fully authenticated")
