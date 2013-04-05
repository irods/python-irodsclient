import struct
import logging
import socket
import xml.etree.ElementTree as ET
from message import Message
from property import BinaryProperty, StringProperty, IntegerProperty, LongProperty, ArrayProperty, SubmessageProperty

class iRODSMessage(object):
    def __init__(self, type=None, msg=None, error=None, bs=None, int_info=None):
        self.type = type
        self.msg = msg
        self.error = error
        self.bs = bs
        self.int_info = int_info

    @staticmethod
    def recv(sock):
        rsp_header_size = sock.recv(4)
        rsp_header_size = struct.unpack(">i", rsp_header_size)[0]
        rsp_header = sock.recv(rsp_header_size, socket.MSG_WAITALL)
        logging.debug(rsp_header)
            
        xml_root = ET.fromstring(rsp_header)
        type = xml_root.find('type').text
        msg_len = int(xml_root.find('msgLen').text)
        err_len = int(xml_root.find('errorLen').text)
        bs_len = int(xml_root.find('bsLen').text)
        int_info = int(xml_root.find('intInfo').text)

        message = sock.recv(msg_len, socket.MSG_WAITALL) if msg_len != 0 else None
        error = sock.recv(err_len, socket.MSG_WAITALL) if err_len != 0 else None
        bs = sock.recv(bs_len, socket.MSG_WAITALL) if bs_len != 0 else None
    
        #if message:
            #logging.debug(message)

        return iRODSMessage(type, message, error, bs, int_info)

    def pack(self):
        main_msg = self.msg.pack() if self.msg else None
        msg_header = "<MsgHeader_PI><type>%s</type><msgLen>%d</msgLen>\
            <errorLen>%d</errorLen><bsLen>%d</bsLen><intInfo>%d</intInfo>\
            </MsgHeader_PI>" % (
                self.type, 
                len(main_msg) if main_msg else 0, 
                len(self.error) if self.error else 0, 
                len(self.bs) if self.bs else 0, 
                self.int_info if self.int_info else 0
            )
        msg_header_length = struct.pack(">i", len(msg_header))
        parts = [x for x in [main_msg, self.error, self.bs] if x is not None]
        msg = msg_header_length + msg_header + "".join(parts)
        return msg

    def get_main_message(self, cls):
        msg = cls()
        logging.debug(self.msg)
        logging.debug(len(self.msg))
        msg.unpack(ET.fromstring(self.msg))
        return msg

#define StartupPack_PI "int irodsProt; int reconnFlag; int connectCnt; str proxyUser[NAME_LEN]; str proxyRcatZone[NAME_LEN]; str clientUser[NAME_LEN]; str clientRcatZone[NAME_LEN]; str relVersion[NAME_LEN]; str apiVersion[NAME_LEN]; str option[NAME_LEN];"
class StartupPack(Message):
    def __init__(self, user=None, zone=None):
        super(StartupPack, self).__init__()
        if user and zone:
            self.irodsProt = 1 
            self.connectCnt = 0
            self.proxyUser = self.clientUser = user
            self.proxyRcatZone = self.clientRcatZone = zone
            self.relVersion = "rods3.2"
            self.apiVersion = "d"
            self.option = ""

    irodsProt = IntegerProperty()
    reconnFlag = IntegerProperty()
    connectCnt = IntegerProperty()
    proxyUser = StringProperty()
    proxyRcatZone = StringProperty()
    clientUser = StringProperty()
    clientRcatZone = StringProperty()
    relVersion = StringProperty()
    apiVersion = StringProperty()
    option = StringProperty()

#define authResponseInp_PI "bin *response(RESPONSE_LEN); str *username;"
class authResponseInp(Message):
    response = BinaryProperty(16)
    username = StringProperty()

class authRequestOut(Message):
    challenge = BinaryProperty(64)

#define InxIvalPair_PI "int iiLen; int *inx(iiLen); int *ivalue(iiLen);"
class InxIvalPair(Message):
    def __init__(self, data=None):
        super(InxIvalPair, self).__init__()
        self.iiLen = 0
        if data:
            self.iiLen = len(data)
            self.inx = data.keys()
            self.ivalue = data.values()

    iiLen = IntegerProperty()
    inx = ArrayProperty(IntegerProperty())
    ivalue = ArrayProperty(IntegerProperty())

#define InxValPair_PI "int isLen; int *inx(isLen); str *svalue[isLen];" 
class InxValPair(Message):
    def __init__(self, data=None):
        super(InxValPair, self).__init__()
        self.isLen = 0
        if data:
            self.isLen = len(data)
            self.inx = data.keys()
            self.svalue = data.values()

    isLen = IntegerProperty()
    inx = ArrayProperty(IntegerProperty())
    svalue = ArrayProperty(StringProperty())

#define KeyValPair_PI "int ssLen; str *keyWord[ssLen]; str *svalue[ssLen];"
class KeyValPair(Message):
    def __init__(self, data=None):
        super(KeyValPair, self).__init__()
        self.ssLen = 0
        if data:
            self.ssLen = len(data)
            self.keyWord = data.keys()
            self.svalue = data.values()

    ssLen = IntegerProperty()
    keyWord = ArrayProperty(StringProperty())
    svalue = ArrayProperty(StringProperty()) 

#define GenQueryInp_PI "int maxRows; int continueInx; int partialStartIndex; int options; struct KeyValPair_PI; struct InxIvalPair_PI; struct InxValPair_PI;"
class GenQueryInp(Message):
    maxRows = IntegerProperty()
    continueInx = IntegerProperty()
    partialStartIndex = IntegerProperty()
    options = IntegerProperty()
    KeyValPair_PI = SubmessageProperty(KeyValPair)
    InxIvalPair_PI = SubmessageProperty(InxIvalPair)
    InxValPair_PI = SubmessageProperty(InxValPair)

#define SqlResult_PI "int attriInx; int reslen; str *value(rowCnt)(reslen);"  
class SqlResult(Message):
    attriInx = IntegerProperty()
    reslen = IntegerProperty()
    value = ArrayProperty(StringProperty())

#define GenQueryOut_PI "int rowCnt; int attriCnt; int continueInx; int totalRowCount; struct SqlResult_PI[MAX_SQL_ATTR];"
class GenQueryOut(Message):
    rowCnt = IntegerProperty()
    attriCnt = IntegerProperty()
    continueInx = IntegerProperty()
    totalRowCount = IntegerProperty()
    SqlResult_PI = ArrayProperty(SubmessageProperty(SqlResult))

#define DataObjInp_PI "str objPath[MAX_NAME_LEN]; int createMode; int openFlags; double offset; double dataSize; int numThreads; int oprType; struct *SpecColl_PI; struct KeyValPair_PI;"
class DataObjInp(Message):
    objPath = StringProperty()
    createMode = IntegerProperty()
    openFlags = IntegerProperty()
    offset = LongProperty()
    dataSize = LongProperty()
    numThreads = IntegerProperty()
    oprType = IntegerProperty()
    KeyValPair_PI = SubmessageProperty(KeyValPair)

#define dataObjReadInp_PI "int l1descInx; int len;"
class dataObjReadInp(Message):
    l1descInx = IntegerProperty()
    len = IntegerProperty()

#define dataObjWriteInp_PI "int dataObjInx; int len;"
class dataObjWriteInp(Message):
    dataObjInx = IntegerProperty()
    len = IntegerProperty()

#define fileLseekInp_PI "int fileInx; double offset; int whence"
class fileLseekInp(Message):
    fileInx = IntegerProperty()
    offset = LongProperty()
    whence = IntegerProperty()

#define fileLseekOut_PI "double offset;"
class fileLseekOut(Message):
    offset = LongProperty()

#define dataObjCloseInp_PI "int l1descInx; double bytesWritten;"
class dataObjCloseInp(Message):
    l1descInx = IntegerProperty()
    bytesWritten = LongProperty()

#define ModAVUMetadataInp_PI "str *arg0; str *arg1; str *arg2; str *arg3; str *arg4; str *arg5; str *arg6; str *arg7;  str *arg8;  str *arg9;"
class ModAVUMetadataInp(Message):
    def __init__(self, *args):
        super(ModAVUMetadataInp, self).__init__()
        for i in range(len(args)):
            setattr(self, 'arg%d' % i, args[i] if args[i] else "")

        print self._values

    arg0 = StringProperty()
    arg1 = StringProperty()
    arg2 = StringProperty()
    arg3 = StringProperty()
    arg4 = StringProperty()
    arg5 = StringProperty()
    arg6 = StringProperty()
    arg7 = StringProperty()
    arg8 = StringProperty()
    arg9 = StringProperty()

def empty_gen_query_out(cols):
    sql_results = [SqlResult(attriInx=col.icat_id, value=[]) for col in cols]
    gqo = GenQueryOut(
        rowCnt=0,
        attriCnt=len(cols),
        SqlResult_PI=sql_results
    )  
    return gqo
