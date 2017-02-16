from irods.query import Query
from irods.pool import Pool
from irods.account import iRODSAccount
from irods.manager.collection_manager import CollectionManager
from irods.manager.data_object_manager import DataObjectManager
from irods.manager.metadata_manager import MetadataManager
from irods.manager.access_manager import AccessManager
from irods.manager.user_manager import UserManager, UserGroupManager
from irods.manager.resource_manager import ResourceManager
from irods.exception import NetworkException
import socket
from irods.api_number import api_number
from irods.message import (
            iRODSMessage, StartupPack, AuthResponse, AuthChallenge,
                OpenedDataObjRequest, FileSeekResponse, StringStringMap, VersionResponse,
                )
from irods.exception import get_exception_by_code, NetworkException

class iRODSSession(object):

    def __init__(self, *args, **kwargs):
        self.pool = None
        if args or kwargs:
            self.configure(*args, **kwargs)

        self.collections = CollectionManager(self)
        self.data_objects = DataObjectManager(self)
        self.metadata = MetadataManager(self)
        self.permissions = AccessManager(self)
        self.users = UserManager(self)
        self.user_groups = UserGroupManager(self)
        self.resources = ResourceManager(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()

    def cleanup(self):
        for conn in self.pool.active | self.pool.idle:
            try:
                conn.disconnect()
            except NetworkException:
                pass
            conn.release(True)

    def configure(self,
                  host=None, port=1247, user=None, zone=None,
                  password=None, client_user=None, client_zone=None,
                  server_dn=None, authentication_scheme='password'):
        account = iRODSAccount(host, int(port), user, zone, authentication_scheme, password, client_user, server_dn, client_zone)
        self.pool = Pool(account)

    def query(self, *args):
        return Query(self, *args)

        # WHY IS THIS HERE?
        # self.host = host
        # self.port = port
        # self.proxy_user = self.client_user = user
        # self.proxy_zone = self.client_zone = zone
    
    def miscsvrinfo(self):
        # implementing functionality of imiscsvrinfo.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print "trying to connect"
        try:
            s.connect((self.host, self.port))
        except socket.error:
            raise NetworkException("Could not connect to specified host and port!")
        print "Creating message"
        msg = iRODSMessage(msg_type='RODS_API_REQ',msg=None,int_info=api_number['GET_MISC_SVR_INFO_AN'])
        print "packing message"
        string = msg.pack()
        print "sending message: ", string
        try:
            self.socket.sendall(string)
        except:
            print "failed to send message!"
            raise NetworkException("Unable to send message")
        try:
            msg = iRODSMEssage.recv(Self.socket)
        except socket.error:
            exit(1)
        if msg.int_info < 0:
            raise get_exception_by_code(msg.int_info)
        print msg
        return msg
        

                    
    @property
    def username(self):
        return self.pool.account.client_user

    @property
    def zone(self):
        return self.pool.account.client_zone

    @property
    def host(self):
        return self.pool.account.host

    @property
    def port(self):
        return self.pool.account.port
