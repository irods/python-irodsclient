import socket 
import hashlib
import struct
import logging
from message import iRODSMessage, StartupPack, authResponseInp, GenQueryOut, DataObjInp, authRequestOut, KeyValPair
from . import MAX_PASSWORD_LENGTH, O_RDONLY
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
        logging.debug(str)
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
        main_message = StartupPack(self.user, self.zone)
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
        challenge_msg = self._recv()
        logging.debug(challenge_msg.msg)
        challenge = challenge_msg.get_main_message(authRequestOut).challenge
        padded_pwd = struct.pack("%ds" % MAX_PASSWORD_LENGTH, self.password)
        m = hashlib.md5()
        m.update(challenge)
        m.update(padded_pwd)
        encoded_pwd = m.digest()

        encoded_pwd = encoded_pwd.replace('\x00', '\x01')
        pwd_msg = authResponseInp(response=encoded_pwd, username=self.user)
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
            return iRODSCollection(self, results[0])

    def get_data_object(self, path):
        if not self.authenticated:
            self._login()
        parent = self.get_collection(dirname(path))
        results = self.query(DataObject)\
            .filter(DataObject.name == basename(path))\
            .filter(DataObject.collection_id == parent.id)\
            .all()
        if results.length == 1:
            return iRODSDataObject(self, parent, results[0])

    def get_file(self, path, mode):
        message_body = DataObjInp(
            objPath=path,
            createMode=0,
            openFlags=O_RDONLY,
            offset=0,
            dataSize=-1,
            numThreads=0,
            oprType=0,
            KeyValPair_PI=KeyValPair(),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body, int_info=602)
        self._send(message)
        response = self._recv()

    def query(self, *args):
        return Query(self, *args)

    def execute_query(self, query):
        if not self.authenticated:
            self._login()
        message_body = query._message()
        message = iRODSMessage('RODS_API_REQ', msg=message_body, int_info=702)
        self._send(message)
        result_message = self._recv()
        results = result_message.get_main_message(GenQueryOut)
        result_set = ResultSet(results)
        return result_set
