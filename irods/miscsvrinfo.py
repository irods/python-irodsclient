import socket
import xml.etree.ElementTree as ET
import time
from irods.api_number import api_number
from irods.message import (
        iRODSMessage, StartupPack
        )
from irods.exception import NetworkException, get_exception_by_code
class miscSvrInfo(object):

    def __init__(self, host=None, port=1247):
        self.host=host
        self.port=port
        self.dummycred=""
        self.miscsvrinfo()
        return

    def miscsvrinfo(self):
        # implementing functionality of imiscsvrinfo.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((self.host, self.port))
        except socket.error:
            raise NetworkException("Could not connect to specified host and port!")
        mainMessage = StartupPack(
                (self.dummycred, self.dummycred),
                (self.dummycred, self.dummycred)
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
        self.serverType     = "RCAT_ENABLED" if int(root[0].text) else "RCAT_DISABLED"
        serverBootTime      = root[1].text
        self.relVersion     = root[2].text
        self.apiVersion     = root[3].text
        self.rodsZone       = root[4].text
        self.upSecs = int(time.time()) - int(serverBootTime)
        #mins = upSecs / 60
        #hr = mins/60
        #mins = mins%60
        #day = hr/24
        #hr = hr%24
        #print "serverType:{0}\nrelVersion:{1}\napiVersion:{2}\nzone:{3}\nup {4} days, {5}:{6}".format(
        #        serverType,relVersion,apiVersion,rodsZone,day,hr,mins)
        s.close()
        return 


#    @property
#    def serverType(self):
#        if int(self.serverType):
#            return 'RCAT_ENABLED'
#        else:
#            return 'RCAT_DISABLED'
#        
#    @property
#    def relVersion(self):
#        return self.relVersion
#    @property
#    def apiVersion(self):
#        return self.apiVersion
#    @property
#    def rodsZone(self):
#        return self.rodsZone
#    @property
#    def uptime(self):
#        return self.upSecs
