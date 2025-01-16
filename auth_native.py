import base64
import hashlib
from irods import MAX_PASSWORD_LENGTH
import logging
import struct
import sys

logging.basicConfig( level = logging.INFO )

import irods.connection, irods.pool, irods.account

from irods.api_number import api_number
from irods.message import iRODSMessage, JSON_Message

class REQUEST_IS_MISSING_KEY(Exception): pass

def throw_if_request_message_is_missing_key( request, required_keys ):
  for key in required_keys:
    if not key in request:
      raise REQUEST_IS_MISSING_KEY(f'key = {key}')

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
        func = getattr(self, next_operation, None)
        if func is None:
            raise RuntimeError("request contains no 'next_operation'")
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
            
    def auth_client_authenticated(self, request):
        resp = request.copy()

        resp["next_operation"] = __FLOW_COMPLETE__
        self.loggedIn = 1;
        return resp


class native_ClientAuthState(ClientAuthState):


    def auth_client_start(self, request):
        resp = request.copy()
        # user_name and zone_name keys injected by authenticate_client() method
        resp[__NEXT_OPERATION__] = self.AUTH_CLIENT_AUTH_REQUEST # native_auth_client_request
        return resp

    # Client defines. These strings should match instance method names within the class namespace.
    AUTH_AGENT_START = 'native_auth_agent_start'
    AUTH_CLIENT_AUTH_REQUEST = 'native_auth_client_request'
    AUTH_ESTABLISH_CONTEXT = 'native_auth_establish_context'
    AUTH_CLIENT_AUTH_RESPONSE = 'native_auth_client_response'

    # Server defines.
    AUTH_AGENT_AUTH_REQUEST = "auth_agent_auth_request" 
    AUTH_AGENT_AUTH_RESPONSE = "auth_agent_auth_response"

    def native_auth_client_request(self, request):
        server_req = request.copy()
        server_req[__NEXT_OPERATION__] = self.AUTH_AGENT_AUTH_REQUEST

        resp = _auth_api_request(self.conn, server_req)

        resp[__NEXT_OPERATION__] = self.AUTH_ESTABLISH_CONTEXT
        return resp

    def native_auth_establish_context(self, request):
        throw_if_request_message_is_missing_key(request,
            ["user_name", "zone_name", "request_result"])
        request = request.copy()

        password = self.conn.account.password
        if not password:
            # TODO : move 'get_obfuscated_password' to a common import module (auth_utils ?)
            # --- Note this was added so auth_pam_password.py could validate using a new .irodsA which it wrote!
            import auth_pam_password
            password = auth_pam_password.get_obfuscated_password()
        challenge = request["request_result"].encode('utf-8')
        self.conn._client_signature = "".join("{:02x}".format(c) for c in challenge[:16])

        padded_pwd = struct.pack(
            "%ds" % MAX_PASSWORD_LENGTH, password.encode(
                'utf-8').strip())

        m = hashlib.md5()
        m.update(challenge)
        m.update(padded_pwd)

        encoded_pwd = m.digest()
        if b'\x00' in encoded_pwd:
            encoded_pwd_array = bytearray(encoded_pwd)
            encoded_pwd = bytes(encoded_pwd_array.replace(b'\0', b'\1'))
        request['digest'] = base64.encodebytes(encoded_pwd).strip().decode('utf-8')

        request[__NEXT_OPERATION__] = self.AUTH_CLIENT_AUTH_RESPONSE
        return request

    def native_auth_client_response (self,request):
        throw_if_request_message_is_missing_key(request,
            ["user_name", "zone_name", "digest"])

        server_req = request.copy()
        server_req[__NEXT_OPERATION__] = self.AUTH_AGENT_AUTH_RESPONSE
        resp = _auth_api_request(self.conn, server_req)

        self.loggedIn = 1;
        resp [__NEXT_OPERATION__] = __FLOW_COMPLETE__
        return resp


_scheme = 'native'

def authenticate_native( conn, req = {} ):
    logging.info('----------- native (begin)')
    # rename 'initial_request' as 'context' ?
    native_ClientAuthState(
        conn, 
        scheme = _scheme
    ).authenticate_client( initial_request = req )
    logging.info('----------- native (end)')

if __name__ == '__main__':

    User, Zone, Pw = sys.argv[1:4]

    account = irods.account.iRODSAccount(
      'localhost',1247,
      User, Zone,
      password = Pw,
      irods_authentication_scheme = _scheme
    )

#   from irods.auth import AuthStorage
#   astor = AuthStorage(account)

    pool = irods.pool.Pool(account)
    connection = irods.connection.Connection(pool, account, connect = False)

    authenticate_native(
        connection, 
        req = {'user_name': account.proxy_user,
               'zone_name': account.proxy_zone} )

