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
import xml.etree.ElementTree as ET
import time
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
        try:
            s.connect((self.host, self.port))
        except socket.error:
            raise NetworkException("Could not connect to specified host and port!")
        mainMessage = StartupPack(
                (self.pool.account.proxy_user, self.pool.account.proxy_zone),
                (self.pool.account.client_user, self.pool.account.client_zone)
        )

        msg = iRODSMessage(msg_type='RODS_CONNECT',msg=mainMessage)
        string = msg.pack()
        try:
            s.sendall(string)
        except:
            raise NetworkException("Unable to send message")
        try:
            msg = iRODSMessage.recv(s)
        except socket.error:
            exit(1)
        if msg.int_info < 0:
            raise get_exception_by_code(msg.int_info)


        # do the miscsvrrequest here
        msg = iRODSMessage(msg_type='RODS_API_REQ',msg=None,int_info=api_number['GET_MISC_SVR_INFO_AN'])
        string = msg.pack()
        #print "miscsvrionfo request message\n",string
        try:
            s.sendall(string)
        except:
            raise NetworkException("Unable to send message")
        try:
            miscsvrinfo = iRODSMessage.recv(s)
        except socket.error:
            exit(1)
        if msg.int_info < 0:
            raise get_exception_by_code(msg.int_info)
        #print "miscsvrinfo reply:\n\n",miscsvrinfo.msg
        root = ET.fromstring(miscsvrinfo.msg)
        serverType     = root[0].text
        serverBootTime = root[1].text
        relVersion     = root[2].text
        apiVersion     = root[3].text
        rodsZone       = root[4].text
        upSecs = int(time.time()) - int(serverBootTime)
        mins = upSecs / 60
        hr = mins/60
        mins = mins%60
        day = hr/24
        hr = hr%24
        print "serverType:{0}\nrelVersion:{1}\napiVersion:{2}\nzone:{3}\nup {4} days, {5}:{6}".format(
                serverType,relVersion,apiVersion,rodsZone,day,hr,mins)
        return (serverType,relVersion,apiVersion,rodsZone,upSecs)

        return miscsvrinfo.msg
        

                    
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
