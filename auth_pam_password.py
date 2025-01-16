import base64
import getpass
import hashlib
from irods import MAX_PASSWORD_LENGTH
import irods.password_obfuscation as obf
import irods.session
import logging
import ssl
import struct
import sys
#from .auth_native import authenticate_native
from auth_native import authenticate_native

logging.basicConfig( level = logging.INFO )

import irods.connection, irods.pool, irods.account

from irods.api_number import api_number
from irods.message import iRODSMessage, JSON_Message

class REQUEST_IS_MISSING_KEY(Exception): pass

def throw_if_request_message_is_missing_key( request, required_keys ):
  for key in required_keys:
    if not key in request:
      raise REQUEST_IS_MISSING_KEY(f"key = {key}")

# General implementation to mirror iRODS cli/srv authentication framework

def _auth_api_request(conn, data):
    message_body = JSON_Message(data, conn.server_version)
    message = iRODSMessage('RODS_API_REQ', msg=message_body,
        int_info=api_number['AUTHENTICATION_APN']
    )
    conn.send(message)
    response = conn.recv()
    return response.get_json_encoded_struct()

class ClientAuthError(Exception):
    pass

__FLOW_COMPLETE__ = "authentication_flow_complete"
__NEXT_OPERATION__ = "next_operation"

# __ state machine with methods named for the operations valid on the client. __

class ClientAuthState:

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

FORCE_PASSWORD_PROMPT = "force_password_prompt"
AUTH_PASSWORD_KEY = "a_pw"

def get_pam_password_from_stdin():
    if sys.stdin.isatty():
        return getpass.getpass('Please enter PAM Password: ')
    else:
        return sys.stdin.readline().strip()

def get_obfuscated_password():
    return irods.session.iRODSSession.get_irods_password()

def set_obfuscated_password(to_encode):
    with open(irods.session.iRODSSession.get_irods_password_file(),'w') as irodsA:
        irodsA.write(obf.encode(to_encode))

class pam_password_ClientAuthState(authentication_base):

    def __init__(self, *a, check_ssl = True, **kw): 
        super().__init__(*a,**kw)
        self.check_ssl =  check_ssl

    def auth_client_start(self, request):

        if self.check_ssl:
            if not isinstance(self.conn.socket, ssl.SSLSocket):
                msg = 'Need to be connected via SSL.'
                raise RuntimeError(msg)

        resp = request.copy()

        if resp.pop(FORCE_PASSWORD_PROMPT, None):
            resp[AUTH_PASSWORD_KEY] = get_pam_password_from_stdin()
        else:
            pw = get_obfuscated_password()
            if pw:
                resp[__NEXT_OPERATION__] = self.perform_native_auth
                return resp
            resp[AUTH_PASSWORD_KEY] = get_pam_password_from_stdin()

        resp[__NEXT_OPERATION__] = self.AUTH_CLIENT_AUTH_REQUEST
        return resp

    # Client define
    AUTH_CLIENT_AUTH_REQUEST = 'pam_password_auth_client_request'
    # Server define
    AUTH_AGENT_AUTH_REQUEST = "auth_agent_auth_request"

    def pam_password_auth_client_request(self, request):
        server_req = request.copy()
        server_req[__NEXT_OPERATION__] = self.AUTH_AGENT_AUTH_REQUEST

        resp = _auth_api_request(self.conn, server_req)
        throw_if_request_message_is_missing_key(resp, {"request_result"})
        
        set_obfuscated_password(resp["request_result"])
        resp[__NEXT_OPERATION__] = self.perform_native_auth
        return resp


    def pam_password_auth_client_perform_native_auth(self, request):
        resp = request.copy()
        resp.pop(AUTH_PASSWORD_KEY, None)

        authenticate_native(self.conn, request)

        resp["next_operation"] = __FLOW_COMPLETE__
        self.loggedIn = 1;
        return resp

    perform_native_auth = pam_password_auth_client_perform_native_auth 

# ==========================================================

_scheme = 'pam_password'

if __name__ == '__main__':
    User, Zone, Pw = sys.argv[1:4]
    
    account = irods.account.iRODSAccount(
      'localhost',1247,
      User, Zone,
      #password = Pw, ## -- We'll be getting a password prompt from stdin or spec_password member instead
      irods_authentication_scheme = _scheme
    )

    pool = irods.pool.Pool(account)
    connection = irods.connection.Connection(pool, account, connect = False)

    state = pam_password_ClientAuthState(
        connection, 
        scheme = _scheme,

# TODO remove this line for testing without SSL:
        check_ssl = False
    )

    state.authenticate_client(
        initial_request = {'user_name': account.proxy_user,
                           'zone_name': account.proxy_zone,
                          })
