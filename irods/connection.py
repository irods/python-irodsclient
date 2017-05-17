from __future__ import absolute_import
import socket
import logging
import struct
import hashlib
import six


from irods.message import (
    iRODSMessage, StartupPack, AuthResponse, AuthChallenge,
    OpenedDataObjRequest, FileSeekResponse, StringStringMap, VersionResponse,
    GSIAuthMessage)
from irods.exception import get_exception_by_code, NetworkException
from irods import (
    MAX_PASSWORD_LENGTH, RESPONSE_LEN,
    AUTH_SCHEME_KEY, GSI_AUTH_PLUGIN, GSI_AUTH_SCHEME, GSI_OID
)
from irods.api_number import api_number

logger = logging.getLogger(__name__)


class Connection(object):

    def __init__(self, pool, account):

        self.pool = pool
        self.socket = None
        self.account = account
        self._server_version = self._connect()

        scheme = self.account.authentication_scheme

        if scheme == 'password':
            self._login_password()
        elif scheme == 'gsi':
            self.client_ctx = None
            self._login_gsi()
        else:
            raise ValueError("Unknown authentication scheme %s" % scheme)

    def __del__(self):
        if self.socket:
            self.disconnect()

    def send(self, message):
        string = message.pack()

        logger.debug(string)
        try:
            #print(string)
            self.socket.sendall(string)
        except:
            logger.error(
                "Unable to send message. " +
                "Connection to remote host may have closed. " +
                "Releasing connection from pool."
            )
            self.release(True)
            raise NetworkException("Unable to send message")

    def recv(self):
        try:
            msg = iRODSMessage.recv(self.socket)
        except socket.error:
            logger.error("Could not receive server response")
            self.release(True)
            raise NetworkException("Could not receive server response")
        if msg.int_info < 0:
            raise get_exception_by_code(msg.int_info)
        return msg

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def release(self, destroy=False):
        self.pool.release_connection(self, destroy)

    def reply(self, api_reply_index):
        value = socket.htonl(api_reply_index)
        try:
            self.socket.sendall(struct.pack('I', value))
        except:
            self.release(True)
            raise NetworkException("Unable to send API reply")

    def _connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            s.connect((self.account.host, self.account.port))
        except socket.error:
            raise NetworkException(
                "Could not connect to specified host and port: " +
                "{host}:{port}".format(
                    host=self.account.host, port=self.account.port))

        self.socket = s
        main_message = StartupPack(
            (self.account.proxy_user, self.account.proxy_zone),
            (self.account.client_user, self.account.client_zone)
        )

        msg = iRODSMessage(msg_type='RODS_CONNECT', msg=main_message)
        self.send(msg)

        # server responds with version
        version_msg = self.recv()
        return version_msg.get_main_message(VersionResponse)

    @property
    def server_version(self):
        return self._server_version.relVersion

    def disconnect(self):
        disconnect_msg = iRODSMessage(msg_type='RODS_DISCONNECT')
        self.send(disconnect_msg)
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()
        self.socket = None

    def recvall(self, n):
        # Helper function to recv n bytes or return None if EOF is hit
        data = b''
        while len(data) < n:
            packet = self.socket.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    def init_sec_context(self):
        import gssapi

        # AUTHORIZATION MECHANISM
        gsi_mech = gssapi.raw.OID.from_int_seq(GSI_OID)

        # SERVER NAME
        server_name = gssapi.Name(self.account.server_dn)
        server_name.canonicalize(gsi_mech)

        # CLIENT CONTEXT
        self.client_ctx = gssapi.SecurityContext(
            name=server_name,
            mech=gsi_mech,
            flags=[2, 4],
            usage='initiate')

    def send_gsi_token(self, server_token=None):

        # CLIENT TOKEN
        if server_token is None:
            client_token = self.client_ctx.step()
        else:
            client_token = self.client_ctx.step(server_token)
        logger.debug("[GSI handshake] Client: sent a new token")

        # SEND IT TO SERVER
        self.reply(len(client_token))
        self.socket.sendall(client_token)

    def receive_gsi_token(self):

        # Receive client token from iRODS
        data = self.socket.recv(4)
        value = struct.unpack("I", bytearray(data))
        token_len = socket.ntohl(value[0])
        server_token = self.recvall(token_len)
        logger.debug("[GSI handshake] Server: received a new token")

        return server_token

    def handshake(self, target):
        """
        This GSS API context based on GSI was obtained combining 2 sources:
    https://pythonhosted.org/gssapi/basic-tutorial.html
    https://github.com/irods/irods_auth_plugin_gsi/blob/master/gsi/libgsi.cpp
        """

        self.init_sec_context()

        # Go, into the loop
        self.send_gsi_token()

        while not (self.client_ctx.complete):

            server_token = self.receive_gsi_token()

            self.send_gsi_token(server_token)

        logger.debug("[GSI Handshake] completed")

    def gsi_client_auth_request(self):

        # Request for authentication with GSI on current user
        message_body = GSIAuthMessage(
            auth_scheme_=GSI_AUTH_PLUGIN,
            context_='a_user=%s' % self.account.client_user
        )
        # GSI = 1201
# https://github.com/irods/irods/blob/master/lib/api/include/apiNumber.h#L158
        auth_req = iRODSMessage(
            msg_type='RODS_API_REQ', msg=message_body, int_info=1201)
        self.send(auth_req)
        # Getting the challenge message
        self.recv()

        # This receive an empty message for confirmation... To check:
        # challenge_msg = self.recv()

    def gsi_client_auth_response(self):

        message = '%s=%s' % (AUTH_SCHEME_KEY, GSI_AUTH_SCHEME)
        # IMPORTANT! padding
        len_diff = RESPONSE_LEN - len(message)
        message += "\0" * len_diff

        # mimic gsi_auth_client_response
        gsi_msg = AuthResponse(
            response=message,
            username=self.account.proxy_user + '#' + self.account.proxy_zone
        )
        gsi_request = iRODSMessage(
            msg_type='RODS_API_REQ', int_info=704, msg=gsi_msg)
        self.send(gsi_request)
        self.recv()
        # auth_response = self.recv()

    def _login_gsi(self):
        # Send iRODS server a message to request GSI authentication
        self.gsi_client_auth_request()

        # Create a context handshaking GSI credentials
        # Note: this can work only if you export GSI certificates
        # as shell environment variables (X509_etc.)
        self.handshake(self.account.host)

        # Complete the protocol
        self.gsi_client_auth_response()

        logger.info("GSI authorization validated")

    def read_file(self, desc, size):
        message_body = OpenedDataObjRequest(
            l1descInx=desc,
            len=size,
            whence=0,
            oprType=0,
            offset=0,
            bytesWritten=0,
            KeyValPair_PI=StringStringMap()
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_READ_AN'])

        logger.debug(desc)
        self.send(message)
        response = self.recv()
        return response.bs

    def _login_password(self):

        # authenticate
        auth_req = iRODSMessage(msg_type='RODS_API_REQ', int_info=703)
        self.send(auth_req)

        # challenge
        challenge_msg = self.recv()
        logger.debug(challenge_msg.msg)
        challenge = challenge_msg.get_main_message(AuthChallenge).challenge
        if six.PY3:
            challenge = challenge.encode('utf-8').strip()
            padded_pwd = struct.pack(
                "%ds" % MAX_PASSWORD_LENGTH, self.account.password.encode(
                    'utf-8').strip())
        else:
            padded_pwd = struct.pack(
                "%ds" % MAX_PASSWORD_LENGTH, self.account.password)
        m = hashlib.md5()
        m.update(challenge)
        m.update(padded_pwd)
        encoded_pwd = m.digest()

        if six.PY2:
            encoded_pwd = encoded_pwd.replace('\x00', '\x01')
        elif b'\x00' in encoded_pwd:
            encoded_pwd_array = bytearray(encoded_pwd)
            encoded_pwd = bytes(encoded_pwd_array.replace(b'\x00', b'\x01'))

        pwd_msg = AuthResponse(
            response=encoded_pwd, username=self.account.proxy_user)
        pwd_request = iRODSMessage(
            msg_type='RODS_API_REQ', int_info=704, msg=pwd_msg)
        self.send(pwd_request)
        self.recv()

    def write_file(self, desc, string):
        message_body = OpenedDataObjRequest(
            l1descInx=desc,
            len=len(string),
            whence=0,
            oprType=0,
            offset=0,
            bytesWritten=0,
            KeyValPair_PI=StringStringMap()
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               bs=string,
                               int_info=api_number['DATA_OBJ_WRITE_AN'])
        self.send(message)
        response = self.recv()
        return response.int_info

    def seek_file(self, desc, offset, whence):
        message_body = OpenedDataObjRequest(
            l1descInx=desc,
            len=0,
            whence=whence,
            oprType=0,
            offset=offset,
            bytesWritten=0,
            KeyValPair_PI=StringStringMap()
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_LSEEK_AN'])

        self.send(message)
        response = self.recv()
        offset = response.get_main_message(FileSeekResponse).offset
        return offset

    def close_file(self, desc, options=None):
        message_body = OpenedDataObjRequest(
            l1descInx=desc,
            len=0,
            whence=0,
            oprType=0,
            offset=0,
            bytesWritten=0,
            KeyValPair_PI=StringStringMap(options)
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_CLOSE_AN'])

        self.send(message)
        self.recv()
