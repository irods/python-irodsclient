import socket
import xml.etree.ElementTree as ET
import time
from irods.api_number import api_number
from irods.message import (iRODSMessage, StartupPack)
from irods.exception import NetworkException, get_exception_by_code

# irods.miscsvrinfo by Baran Balkan (github.com/bascibaran)
#
# analogue to icommand imiscsvrinfo. 
# the object is essentially the struct that the icommand uses to get the info.
# the different components of imiscsvrinfo's return payload, eg serverType, boot time, etc
# are attributes of the instance. 
#
# example usage: 
# from irods.miscsvrinfo import iMiscSvrInfo
# m = iMiscSvrInfo('myirodshost.domain.net')
# m.serverBootTime     # boot time of the server(seconds since the beginning of epoch)
# m.serverType # RCAT enabled or disabled
# and so on. 

# print m # yields the same output as imiscsvrinfo
# the property of the object gives us the boot time of the server
# but the string representation of the object
# computes and displays the uptime in human readable format, 
# in its emulation of the output of imiscsvrinfo. 

class iMiscSvrInfo(object):

    def __init__(self, host=None, port=1247):
        self.host=host
        self.port=port
        self.dummycred=""
        self._rodsZone            = None
        self._relVersion          = None
        self._apiVersion          = None
        self._serverType          = None
        self._serverBootTime      = None
        self.setInfo()
        return

    def setInfo(self):
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

        msg = iRODSMessage(msg_type='RODS_API_REQ',msg=None,int_info=api_number['GET_MISC_SVR_INFO_AN'])
        string = msg.pack()
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

        root = ET.fromstring(miscsvrinfo.msg)
        self.setProps( "RCAT_ENABLED" if int(root[0].text) else "RCAT_DISABLED",
            root[2].text,
            root[3].text,
            root[4].text,
            int(root[1].text))
        s.close()
        return
  
    def setProps(self, st, rv, av, rz, bt):
        self._serverType         = st
        self._relVersion         = rv
        self._apiVersion         = av
        self._rodsZone           = rz
        self._serverBootTime     = bt

    def __str__(self):
        uptime = (int(time.time()) - self.serverBootTime)
        mins = uptime / 60
        hr   = mins/60
        mins = mins%60
        day = hr/24
        hr = hr%24
        return "{0}\nrelVersion={1}\napiVersion={2}\nrodsZone={3}\nup {4} days, {5}:{6}".format(
            self.serverType,self.relVersion,self.apiVersion,self.rodsZone,day,hr,mins)
   
    @property
    def serverType(self):
        return self._serverType
    @property
    def relVersion(self):
        return self._relVersion
    @property
    def apiVersion(self):
        return self._apiVersion
    @property
    def rodsZone(self):
        return self._rodsZone
    @property
    def serverBootTime(self):
        return self._serverBootTime
