import socket
import logging
import struct
import hashlib
import logging
from message import iRODSMessage, StartupPack, authRequestOut, authResponseInp
from exception import get_exception_by_code
from . import MAX_PASSWORD_LENGTH

class Connection(object):
    def __init__(self, pool, account):
        self.pool = pool
        self.socket = None
        self.account = account
        self._connect()
        self._login()

    def __del__(self):
        if self.socket:
            self.disconnect()

    def send(self, message):
        str = message.pack()
        logging.debug(str)
        return self.socket.sendall(str)

    def recv(self):
        msg = iRODSMessage.recv(self.socket)
        if msg.int_info < 0:
            raise get_exception_by_code(msg.int_info)
        return msg

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def release(self):
        self.pool.release_connection(self)

    def _connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            s.connect((self.account.host, self.account.port))
        except socket.error:
            raise Exception("Could not connect to specified host and port: %s:%s" % (self.account.host, self.account.post))

        self.socket = s
        main_message = StartupPack(self.account.user, self.account.zone)
        msg = iRODSMessage(type='RODS_CONNECT', msg=main_message)
        self.send(msg)
        version_msg = self.recv()

    def disconnect(self):
        disconnect_msg = iRODSMessage(type='RODS_DISCONNECT')
        self.send(disconnect_msg)
        self.socket.close()

    def _login(self):
        # authenticate
        auth_req = iRODSMessage(type='RODS_API_REQ', int_info=703)
        self.send(auth_req)

        # challenge
        challenge_msg = self.recv()
        logging.debug(challenge_msg.msg)
        challenge = challenge_msg.get_main_message(authRequestOut).challenge
        padded_pwd = struct.pack("%ds" % MAX_PASSWORD_LENGTH, self.account.password)
        m = hashlib.md5()
        m.update(challenge)
        m.update(padded_pwd)
        encoded_pwd = m.digest()

        encoded_pwd = encoded_pwd.replace('\x00', '\x01')
        pwd_msg = authResponseInp(response=encoded_pwd, username=self.account.user)
        pwd_request = iRODSMessage(type='RODS_API_REQ', int_info=704, msg=pwd_msg)
        self.send(pwd_request)

        auth_response = self.recv()
