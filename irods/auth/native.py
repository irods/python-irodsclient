import base64
import logging
import hashlib
import struct

from irods import MAX_PASSWORD_LENGTH

from . import (__NEXT_OPERATION__, __FLOW_COMPLETE__,
    AuthStorage,
    authentication_base, _auth_api_request,
    throw_if_request_message_is_missing_key)


def login(conn):
    ## short-cut back to the 4.2 logic:
    #conn._login_native()

    authenticate_native(conn,
        req = {'user_name': conn.account.proxy_user,
               'zone_name': conn.account.proxy_zone} )


_scheme = 'native'


def authenticate_native( conn, req = None ):

    logging.info('----------- native (begin)')

    # Default request value (None) assumes the conn.account has been initialized with the normal authentication
    # params such as user, zone, host, port, password, etc., because in normal PRC operation this has all been
    # seen to by the iRODSSession constructor.
    if req is None:
        req = {'user_name': conn.account.proxy_user,
               'zone_name': conn.account.proxy_zone}

    native_ClientAuthState(
        conn,
        scheme = _scheme
    ).authenticate_client(
        # TODO - Q: should we rename 'initial_request' as 'context'?
        initial_request = req
    )

    logging.info('----------- native (end)')


class native_ClientAuthState(authentication_base):

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

        password = ''
        depot = AuthStorage.get_temp_pw_storage(self.conn)
        if depot:
            # The following is how pam_password communicates a server-generated password.
            password = depot.retrieve_pw()

        if not password:
            password = self.conn.account.password or ''

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

#if __name__ == '__main__':
#    from sys import argv
def main(*argv):

    User, Zone, Pw = argv[1:4]

    import irods.account, irods.pool, irods.connection

    account = irods.account.iRODSAccount(
      'localhost',1247,
      User, Zone,
      password = Pw,
      irods_authentication_scheme = _scheme
    )

    pool = irods.pool.Pool(account)
    connection = irods.connection.Connection(pool, account,  #connect=False #TODO delete
    )

    authenticate_native(
        connection,
        req = {'user_name': account.proxy_user,
               'zone_name': account.proxy_zone} )

