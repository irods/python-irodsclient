import socket 
import hashlib
import struct
import logging
from message import iRODSMessage, StartupPack, AuthResponseInp, GenQueryOut
from . import MAX_PASSWORD_LENGTH
from query import Query
from exception import iRODSException
from results import ResultSet
from models import Collection, DataObject
from os.path import basename, dirname
from collection import iRODSCollection
from data_object import iRODSDataObject

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
        #logging.debug(str)
        return self.socket.send(str)

    def _recv(self):
        msg = iRODSMessage.recv(self.socket)
        if msg.int_info < 0:
            raise iRODSException(msg.int_info)
        return msg

    def _connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            s.connect((self.host, self.port))
        except socket.error:
            raise Exception("Could not connect to specified host and port")

        self.socket = s
        main_message = StartupPack(user=self.user, zone=self.zone)
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
        pwd_msg = AuthResponseInp(encoded_pwd, self.user)
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
        query = self.query(Collection).filter(Collection.name == path)
        results = self.execute_query(query)
        if results.length == 1:
            return iRODSCollection(results[0])

    def get_data_object(self, path):
        if not self.authenticated:
            self._login()
        parent = self.get_collection(dirname(path))
        results = self.query(DataObject)\
            .filter(DataObject.name == basename(path))\
            .filter(DataObject.collection_id == parent.id)\
            .all()
        if results.length == 1:
            return iRODSDataObject(results[0])

    def query(self, *args):
        return Query(self, *args)

    def execute_query(self, query):
        if not self.authenticated:
            self._login()
        message_body = query._message()
        message = iRODSMessage('RODS_API_REQ', msg=message_body, int_info=702)
        self._send(message)
        result_message = self._recv()
        results = GenQueryOut.unpack(result_message.msg)
        result_set = ResultSet(results)
        return result_set

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
