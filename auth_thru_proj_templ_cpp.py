import logging
logging.basicConfig( level = logging.INFO )

import irods.connection, irods.pool, irods.account

from irods.api_number import api_number
from irods.message import iRODSMessage, JSON_Message

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

FLOW_COMPLETE = "authentication_flow_complete"

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
            next_operation = resp.get("next_operation")
            if next_operation is None:
              raise ClientAuthError("next_operation key missing; cannot determine next operation")
            if next_operation in (FLOW_COMPLETE,""):
              raise ClientAuthError("authentication flow stopped without success")
            to_send = resp
            
        logging.info("fully authenticated")
            
    # ----------------------------------

    def auth_client_operation(self, request):
        server_req = request.copy()
        server_req["next_operation"] = "auth_agent_operation"

        resp = _auth_api_request(self.conn, server_req)

        resp["next_operation"] = "auth_client_authenticated"
        return resp

    def auth_client_start(self, request):
        server_req = request.copy()
        server_req["next_operation"] = "auth_agent_start"

        resp = _auth_api_request(self.conn, server_req)

        resp["next_operation"] = "auth_client_operation"
        return resp

    def auth_client_authenticated(self, request):
        resp = request.copy()

        resp["next_operation"] = FLOW_COMPLETE
        self.loggedIn = 1;
        return resp

# __ main program __

_scheme = 'project_template_cpp'

account = irods.account.iRODSAccount(
  'localhost',1247,
  'rods','tempZone',
  irods_authentication_scheme = _scheme
)

pool = irods.pool.Pool(account)
connection = irods.connection.Connection(pool,account,connect = False)

state = ClientAuthState(
    connection, 
    scheme = _scheme
)
state.authenticate_client()
