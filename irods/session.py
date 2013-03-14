import socket 
import hashlib
import struct
import logging
from message import iRODSMessage, StartupMessage, ChallengeResponseMessage
from . import MAX_PASSWORD_LENGTH
from file import iRODSCollection

class iRODSSession(object):
    def __init__(self, host=None, port=None, user=None, zone=None, password=None):
        self.host = host
        self.port = port
        self.user = user
        self.zone = zone
        self.password = password    
        self.socket = None
        self.authenticated = False
        self._connect()

    def __del__(self):
        if self.socket:
            self.disconnect()

    def _send(self, message):
        str = message.pack()
        logging.debug(str)
        return self.socket.send(str)

    def _recv(self):
        return iRODSMessage.recv(self.socket)

    def _connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            s.connect((self.host, self.port))
        except socket.error:
            raise Exception("Could not connect to specified host and port")

        self.socket = s
        main_message = StartupMessage(user=self.user, zone=self.zone)
        msg = iRODSMessage(type='RODS_CONNECT', msg=main_message)
        self._send(msg)
        version_msg = self._recv()

    def disconnect(self):
        disconnect_msg = iRODSMessage(type='RODS_DISCONNECT')
        self._send(disconnect_msg)
        self.socket.close()

    def _login(self):
        # authenticate
        auth_req = iRODSMessage(type='RODS_API_REQ', int_info=703)
        self._send(auth_req)

        # challenge
        challenge = self._recv()
        padded_pwd = struct.pack("%ds" % MAX_PASSWORD_LENGTH, self.password)
        m = hashlib.md5()
        m.update(challenge.msg)
        m.update(padded_pwd)
        encoded_pwd = m.digest()

        encoded_pwd = encoded_pwd.replace('\x00', '\x01')
        pwd_msg = ChallengeResponseMessage(encoded_pwd, self.user)
        pwd_request = iRODSMessage(type='RODS_API_REQ', int_info=704, msg=pwd_msg)
        self._send(pwd_request)

        auth_response = self._recv()
        if auth_response.error:
            raise Exception("Unsuccessful login attempt")
        else:
            self.authenticated = True
            logging.debug("Successful login")

    def get_collection(self, path):
        if not self.authenticated:
            self._login()
        return iRODSCollection(self, path)

    def _collection_exists(self, path):
        #define GenQueryInp_PI "int maxRows; int continueInx; int partialStartIndex; int options; struct KeyValPair_PI; struct InxIvalPair_PI; struct InxValPair_PI;"
        """
        <GenQueryInp_PI>
            <maxRows>500</maxRows>
            <continueInx>0</continueInx>
            <partialStartIndex>0</partialStartIndex>
            <options>0</options>
            <KeyValPair_PI>
                <ssLen>0</ssLen>
            </KeyValPair_PI>
            <InxIvalPair_PI>
                <iiLen>1</iiLen>
                <inx>500</inx>
                <ivalue>1</ivalue>
            </InxIvalPair_PI>
            <InxValPair_PI>
                <isLen>1</isLen>
                <inx>501</inx>
                <svalue>= '/tempZone/home/rods'</svalue>
            </InxValPair_PI>
        </GenQueryInp_PI>
        """
