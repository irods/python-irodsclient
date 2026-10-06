from ast import literal_eval as safe_eval
import socket
import logging
import struct
import hashlib
import os
import re
import ssl
import datetime
import errno
from .utility import password_obfuscation as obf

from ..server_constants import LONG_NAME_LEN, MAX_NAME_LEN, MAX_PASSWORD_LENGTH

#from irods.exception import PAM_AUTH_PASSWORD_INVALID_TTL

from .low_level.message import (
    iRODSMessage,
    StartupPack,
    AuthResponse,
    AuthChallenge,
    AuthPluginOut,
    OpenedDataObjRequest,
    FileSeekResponse,
    StringStringMap,
    VersionResponse,
    PluginAuthMessage,
    ClientServerNegotiation,
    Error,
    GetTempPasswordOut,
)

from .low_level.exception import get_exception_by_code, NetworkException, nominal_code
from .low_level import exception as ex
from .low_level.message import PamAuthRequest, PamAuthRequestOut
#
#
## Message to be logged when the connection
## destructor is called. Used in a unit test
DESTRUCTOR_MSG = "connection __del__() called"
 
from ..server_constants import RESPONSE_LEN
from ..connect_constants import NATIVE_AUTH_SCHEME

from .low_level.client_server_negotiation import (
    perform_negotiation,
    validate_policy,
    REQUEST_NEGOTIATION,
    FAILURE,
    USE_SSL,
    REQUIRE_TCP,
    CS_NEG_RESULT_KW
)
from ..api_number import api_number
#
logger = logging.getLogger(__name__)
#
#
 
class Connection:
    def __init__(self, account, authenticate=True, application_name='FPRC'):
        self.application_name = application_name
        self.socket = None
        self.account = account
        self.auth_options = {}
        self._client_signature = None
        self._server_version = self._connect(authenticate)
        self._disconnected = False
        self.authenticated = False

        try:
             
            if not authenticate:
                return
            scheme = self.account._original_authentication_scheme

# ------------- DWM temporarily commented out -------------
#
#            ses = self.pool.session_ref()
#            if ses:
#                ses.resolve_auth_options(scheme, conn=self)
#
#            # These variables are just useful diagnostics.  The login_XYZ() methods should fail by
#            # raising exceptions if they encounter authentication errors.
#            auth_module = auth_type = ""
#
#            if self.server_version >= (4, 3, 0) and not cfg.legacy_auth.force_legacy_auth:
#                import irods.auth
#
#                auth_module = None
#                # use client side "plugin" module: irods.auth.<scheme>
#                irods.auth.load_plugins(subset=[scheme])
#                auth_module = getattr(irods.auth, scheme, None)
#                if auth_module:
#                    auth_module.login(self, **self.auth_options)
#                    auth_type = auth_module.__name__
#            else:
#            ### - LEGACY pre-4.3 authentication

            if 1: #DWM
                auth_type = scheme
                if scheme == NATIVE_AUTH_SCHEME:
                    self._login_native()
                else:
                    auth_type = None
#

            if auth_type:
                self.authenticated = True
            else:
                msg = f"Authentication failed: scheme = {scheme!r}, auth_type = {auth_type!r}, auth_module = {auth_module!r}, "
                raise ValueError(msg)
        finally:
            self.create_time = datetime.datetime.now()
            self.last_used_time = self.create_time
 
    @property
    def server_version(self):
        detected = tuple(int(x) for x in self._server_version.relVersion.replace("rods", "").split("."))
        return detected
#       return safe_eval(os.environ.get("IRODS_SERVER_VERSION", "()")) or detected
#
    @property
    def client_signature(self):
        return self._client_signature

    def __del__(self):
        try:
            self.disconnect()
        except Exception as e:
            logger.info("Exception in finalizer: [%r]", e)
        logger.debug(DESTRUCTOR_MSG)

    def send(self, message):
        string = message.pack()

        logger.debug(string)
        try:
            self.socket.sendall(string)
        except:
            logger.error(
                "Unable to send message. "
                + "Connection to remote host may have closed. "
                + "Releasing connection from pool."
            )
            self.release(True)
            raise NetworkException("Unable to send message")

    def recv(self, into_buffer=None, return_message=(), acceptable_errors=()):
        acceptable_codes = set(nominal_code(e) for e in acceptable_errors)
        try:
            if into_buffer is None:
                msg = iRODSMessage.recv(self.socket)
            else:
                msg = iRODSMessage.recv_into(self.socket, into_buffer)
        except (socket.error, socket.timeout) as e:
            # If _recv_message_in_len() fails in recv() or recv_into(),
            # it will throw a socket.error exception. The exception is
            # caught here, a critical message is logged, and is wrapped
            # in a NetworkException with a more user friendly message
            logger.critical(e)
            logger.error("Could not receive server response")
            self.release(True)
            raise NetworkException("Could not receive server response")
        if isinstance(return_message, list):
            return_message[:] = [msg]
        if msg.int_info < 0:
            try:
                err_msg = iRODSMessage(msg=msg.error).get_main_message(Error).RErrMsg_PI[0].msg
            except TypeError:
                err_msg = None
            if nominal_code(msg.int_info) not in acceptable_codes:
                exc = get_exception_by_code(msg.int_info, err_msg)
                exc.server_msg = msg
                raise exc
        return msg

    def recv_into(self, buffer, **options):
        return self.recv(into_buffer=buffer, **options)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def release(self, destroy=False):
        self.pool.release_connection(self, destroy)

    def reply(self, api_reply_index):
        value = socket.htonl(api_reply_index)
        try:
            self.socket.sendall(struct.pack("I", value))
        except:
            self.release(True)
            raise NetworkException("Unable to send API reply")
#
    def requires_cs_negotiation(self):
        try:
            if self.account.client_server_negotiation == REQUEST_NEGOTIATION:
                return True
        except AttributeError:
            return False
        return False
#
#    @staticmethod
#    def make_ssl_context(irods_account):
#        verify_server = getattr(irods_account, "ssl_verify_server", "hostname")
#        CAfile = getattr(irods_account, "ssl_ca_certificate_file", None)
#        CApath = getattr(irods_account, "ssl_ca_certificate_path", None)
#        verify = ssl.CERT_NONE if ((None is CAfile is CApath) or verify_server == "none") else ssl.CERT_REQUIRED
#        # See https://stackoverflow.com/questions/30461969/disable-default-certificate-verification-in-python-2-7-9/49040695#49040695
#        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=CAfile, capath=CApath)
#        # Note: check_hostname must be assigned prior to verify_mode property or Python library complains!
#        ctx.check_hostname = verify_server == "hostname" and verify != ssl.CERT_NONE
#        ctx.verify_mode = verify
#        return ctx
#
#    def ssl_startup(self):
#        # Get encryption settings from client environment
#        host = self.account.host
#        algo = self.account.encryption_algorithm
#        key_size = self.account.encryption_key_size
#        hash_rounds = self.account.encryption_num_hash_rounds
#        salt_size = self.account.encryption_salt_size
#
#        try:
#            context = self.account.ssl_context
#        except AttributeError:
#            self.account.ssl_context = context = self.make_ssl_context(self.account)
#
#        # Wrap socket with context
#        wrapped_socket = context.wrap_socket(self.socket, server_hostname=(host if context.check_hostname else None))
#
#        # Initial SSL handshake
#        wrapped_socket.do_handshake()
#
#        # Generate key (shared secret)
#        key = os.urandom(self.account.encryption_key_size)
#
#        # Send header-only message with client side encryption settings
#        packed_header = iRODSMessage.pack_header(algo, key_size, salt_size, hash_rounds, 0)
#        wrapped_socket.sendall(packed_header)
#
#        # Send shared secret
#        packed_header = iRODSMessage.pack_header("SHARED_SECRET", key_size, 0, 0, 0)
#        wrapped_socket.sendall(packed_header + key)
#
#        # Use SSL socket from now on
#        self.socket = wrapped_socket
#
    def _connect(self, authenticate=True):
        address = (self.account.host, self.account.port)
        #timeout = self.pool.connection_timeout

        try:
            s = socket.create_connection(address, 
            #timeout
            )
            self._disconnected = False
        except socket.error:
            raise NetworkException("Could not connect to specified host and port: " + "{}:{}".format(*address))

        self.socket = s

        main_message = StartupPack(
            (self.account.proxy_user, self.account.proxy_zone),
            (self.account.client_user, self.account.client_zone),
            self.application_name,
        )

        # No client-server negotiation
        if not self.requires_cs_negotiation():
            if len(main_message.option) >= LONG_NAME_LEN:
                message = "Application name too long."
                raise ValueError(message)
            # Send startup pack without negotiation request
            msg = iRODSMessage(msg_type="RODS_CONNECT", msg=main_message)
            self.send(msg)

            # Server responds with version
            version_msg = self.recv()

            # Done
            return version_msg.get_main_message(VersionResponse)

        # Get client negotiation policy
        client_policy = getattr(self.account, "client_server_policy", REQUIRE_TCP)

        # Sanity check
        validate_policy(client_policy)

        # Send startup pack with negotiation request
        main_message.option = "{}{}".format(main_message.option, REQUEST_NEGOTIATION)
        if len(main_message.option) >= LONG_NAME_LEN:
            message = f"Application name too long when appended with string {REQUEST_NEGOTIATION!r}."
            raise ValueError(message)
        msg = iRODSMessage(msg_type="RODS_CONNECT", msg=main_message)
        self.send(msg)

        # Server responds with its own negotiation policy
        cs_neg_msg = self.recv()
        response = cs_neg_msg.get_main_message(ClientServerNegotiation)
        server_policy = response.result

        # Perform the negotiation
        neg_result, status = perform_negotiation(client_policy=client_policy, server_policy=server_policy)

        # Send negotiation result to server
        client_neg_response = ClientServerNegotiation(
            status=status, result="{}={};".format(CS_NEG_RESULT_KW, neg_result)
        )
        msg = iRODSMessage(msg_type="RODS_CS_NEG_T", msg=client_neg_response)
        self.send(msg)

        # If negotiation failed we're done
        if neg_result == FAILURE:
            self.disconnect()
            raise NetworkException("Client-Server negotiation failure: {},{}".format(client_policy, server_policy))

        # Server responds with version
        version_msg = self.recv()

        if neg_result == USE_SSL:
            self.ssl_startup()

        return version_msg.get_main_message(VersionResponse)
 
    def disconnect(self):
        # Moved the conditions to call disconnect() inside the function.
        # Added a new criteria for calling disconnect(); Only call
        # disconnect() if fileno is not -1 (fileno -1 indicates the socket
        # is already closed). This makes it safe to call disconnect multiple
        # times on the same connection. The first call cleans up the resources
        # and next calls are no-ops
        try:
            if self.socket and getattr(self, "_disconnected", False) == False and self.socket.fileno() != -1:
                disconnect_msg = iRODSMessage(msg_type="RODS_DISCONNECT")
                self.send(disconnect_msg)
                try:
                    # SSL shutdown handshake
                    self.socket = self.socket.unwrap()
                except AttributeError:
                    pass
                try:
                    # BSD/MacOS calls to socket.shutdown() only succeed
                    # if the socket is still open.  Linux and Windows do
                    # not care.  So this call may fail sometimes if the
                    # socket is already closed/disconnected by the OS.
                    # OSError: [Errno 57] Socket is not connected
                    self.socket.shutdown(socket.SHUT_RDWR)
                except OSError as e:
                    # Re-raise if this error is not the known BSD/MacOS error
                    if e.errno != errno.ENOTCONN:
                        raise
                self.socket.close()
        finally:
            self._disconnected = True  # Issue 368 - because of undefined destruction order during interpreter shutdown,
            self.socket = None  # as well as the fact that unhandled exceptions are ignored in __del__, we'd at least
            # like to ensure as much cleanup as possible, thus preventing the above socket shutdown
            # procedure from running too many times and creating confusing messages
#
#    def recvall(self, n):
#        # Helper function to recv n bytes or return None if EOF is hit
#        data = b""
#        while len(data) < n:
#            packet = self.socket.recv(n - len(data))
#            if not packet:
#                return None
#            data += packet
#        return data
#
#    def init_sec_context(self):
#        import gssapi
#
#        # AUTHORIZATION MECHANISM
#        gsi_mech = gssapi.raw.OID.from_int_seq(GSI_OID)
#
#        # SERVER NAME
#        server_name = gssapi.Name(self.account.server_dn)
#        server_name.canonicalize(gsi_mech)
#
#        # CLIENT CONTEXT
#        self.client_ctx = gssapi.SecurityContext(name=server_name, mech=gsi_mech, flags=[2, 4], usage="initiate")
#
#    def send_gsi_token(self, server_token=None):
#
#        # CLIENT TOKEN
#        if server_token is None:
#            client_token = self.client_ctx.step()
#        else:
#            client_token = self.client_ctx.step(server_token)
#        logger.debug("[GSI handshake] Client: sent a new token")
#
#        # SEND IT TO SERVER
#        self.reply(len(client_token))
#        self.socket.sendall(client_token)
#
#    def receive_gsi_token(self):
#
#        # Receive client token from iRODS
#        data = self.socket.recv(4)
#        value = struct.unpack("I", bytearray(data))
#        token_len = socket.ntohl(value[0])
#        server_token = self.recvall(token_len)
#        logger.debug("[GSI handshake] Server: received a new token")
#
#        return server_token
#
#    def handshake(self, target):
#        """
#            This GSS API context based on GSI was obtained combining 2 sources:
#        https://pythonhosted.org/gssapi/basic-tutorial.html
#        https://github.com/irods/irods_auth_plugin_gsi/blob/master/gsi/libgsi.cpp
#        """
#
#        self.init_sec_context()
#
#        # Go, into the loop
#        self.send_gsi_token()
#
#        while not (self.client_ctx.complete):
#            server_token = self.receive_gsi_token()
#
#            self.send_gsi_token(server_token)
#
#        logger.debug("[GSI Handshake] completed")
#
#    def gsi_client_auth_request(self):
#
#        # Request for authentication with GSI on current user
#
#        message_body = PluginAuthMessage(
#            auth_scheme_=GSI_AUTH_PLUGIN,
#            context_="%s=%s" % (AUTH_USER_KEY, self.account.client_user),
#        )
#        # GSI = 1201
#        # https://github.com/irods/irods/blob/master/lib/api/include/apiNumber.h#L158
#        auth_req = iRODSMessage(msg_type="RODS_API_REQ", msg=message_body, int_info=1201)
#        self.send(auth_req)
#        # Getting the challenge message
#        self.recv()
#
#        # This receive an empty message for confirmation... To check:
#        # challenge_msg = self.recv()
#
#    def read_file(self, desc, size=-1, buffer=None):
#        print(f'{desc = }')
#        if size < 0:
#            size = len(buffer)
#        elif buffer is not None:
#            size = min(size, len(buffer))
#        #print('read_it')
#        message_body = OpenedDataObjRequest(
#            l1descInx=desc,
#            len=size,
#            whence=0,
#            oprType=0,
#            offset=0,
#            bytesWritten=0,
#            KeyValPair_PI=StringStringMap(),
#        )
#        message = iRODSMessage("RODS_API_REQ", msg=message_body, int_info=api_number["DATA_OBJ_READ_AN"])
#
#        logger.debug(desc)
#        self.send(message)
#        if buffer is None:
#            response = self.recv()
#        else:
#            response = self.recv_into(buffer)
#
#        return response.bs
#
    def _login_native(self, password=None):

        # Default case, PAM login will send a new password
        if password is None:
            password = self.account.password or ""

        # authenticate
        auth_req = iRODSMessage(msg_type="RODS_API_REQ", int_info=703)
        self.send(auth_req)

        # challenge
        challenge_msg = self.recv()
        logger.debug(challenge_msg.msg)
        challenge = challenge_msg.get_main_message(AuthChallenge).challenge

        # one "session" signature per connection
        # see https://github.com/irods/irods/blob/4.2.1/plugins/auth/native/libnative.cpp#L137
        # and https://github.com/irods/irods/blob/4.2.1/lib/core/src/clientLogin.cpp#L38-L60
        self._client_signature = "".join("{:02x}".format(c) for c in challenge[:16])

        challenge = challenge.strip()
        padded_pwd = struct.pack("%ds" % MAX_PASSWORD_LENGTH, password.encode("utf-8").strip())

        m = hashlib.md5()
        m.update(challenge)
        m.update(padded_pwd)
        encoded_pwd = m.digest()

        if b"\x00" in encoded_pwd:
            encoded_pwd_array = bytearray(encoded_pwd)
            encoded_pwd = bytes(encoded_pwd_array.replace(b"\x00", b"\x01"))

        pwd_msg = AuthResponse(response=encoded_pwd, username=self.account.proxy_user)
        pwd_request = iRODSMessage(
            msg_type="RODS_API_REQ",
            int_info=api_number["AUTH_RESPONSE_AN"],
            msg=pwd_msg,
        )
        self.send(pwd_request)
        self.recv()
        logger.info("Native authorization validated (in legacy auth).")

#    def write_file(self, desc, string):
#        message_body = OpenedDataObjRequest(
#            l1descInx=desc,
#            len=len(string),
#            whence=0,
#            oprType=0,
#            offset=0,
#            bytesWritten=0,
#            KeyValPair_PI=StringStringMap(),
#        )
#        message = iRODSMessage(
#            "RODS_API_REQ",
#            msg=message_body,
#            bs=string,
#            int_info=api_number["DATA_OBJ_WRITE_AN"],
#        )
#        self.send(message)
#        response = self.recv()
#        return response.int_info
#
#    def seek_file(self, desc, offset, whence):
#        message_body = OpenedDataObjRequest(
#            l1descInx=desc,
#            len=0,
#            whence=whence,
#            oprType=0,
#            offset=offset,
#            bytesWritten=0,
#            KeyValPair_PI=StringStringMap(),
#        )
#        message = iRODSMessage("RODS_API_REQ", msg=message_body, int_info=api_number["DATA_OBJ_LSEEK_AN"])
#
#        self.send(message)
#        response = self.recv()
#        offset = response.get_main_message(FileSeekResponse).offset
#        return offset
#
#    def close_file(self, desc, **options):
#        message_body = OpenedDataObjRequest(
#            l1descInx=desc,
#            len=0,
#            whence=0,
#            oprType=0,
#            offset=0,
#            bytesWritten=0,
#            KeyValPair_PI=StringStringMap(options),
#        )
#        message = iRODSMessage("RODS_API_REQ", msg=message_body, int_info=api_number["DATA_OBJ_CLOSE_AN"])
#
#        self.send(message)
#        self.recv()
#
#    def temp_password(self):
#        request = iRODSMessage("RODS_API_REQ", msg=None, int_info=api_number["GET_TEMP_PASSWORD_AN"])
#
#        # Send and receive request
#        self.send(request)
#        response = self.recv()
#        logger.debug(response.int_info)
#
#        # Convert and return answer
#        msg = response.get_main_message(GetTempPasswordOut)
#        return obf.create_temp_password(msg.stringToHashWith, self.account.password)
