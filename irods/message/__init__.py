import struct
import logging
import socket
import xml.etree.ElementTree as ET
from irods.message.message import Message
from irods.message.property import (BinaryProperty, StringProperty,
                                    IntegerProperty, LongProperty, ArrayProperty,
                                    SubmessageProperty)

logger = logging.getLogger(__name__)

IRODS_VERSION = (4, 3, 0, 'd')

try:
    # Python 2
    UNICODE = unicode
except NameError:
    # Python 3
    UNICODE = str


def _recv_message_in_len(sock, size):
    size_left = size
    retbuf = None
    while size_left > 0:
        try:
            buf = sock.recv(size_left, socket.MSG_WAITALL)
        except (AttributeError, ValueError):
            buf = sock.recv(size_left)
        except OSError as e:
            #skip only Windows error 10045 
            if getattr(e, 'winerror', 0) != 10045:
                raise
            buf = sock.recv(size_left)
        size_left -= len(buf)
        if retbuf is None:
            retbuf = buf
        else:
            retbuf += buf
    return retbuf


def _recv_message_into(sock, buffer, size):
    size_left = size
    index = 0
    mv = memoryview(buffer)
    while size_left > 0:
        try:
            rsize = sock.recv_into(mv[index:], size_left, socket.MSG_WAITALL)
        except (AttributeError, ValueError):
            rsize = sock.recv_into(mv[index:], size_left)
        except OSError as e:
            #skip only Windows error 10045 
            if getattr(e, 'winerror', 0) != 10045:
                raise
            rsize = sock.recv_into(mv[index:], size_left)
        size_left -= rsize
        index += rsize
    return mv[:index]


class iRODSMessage(object):

    def __init__(self, msg_type=b'', msg=None, error=b'', bs=b'', int_info=0):
        self.msg_type = msg_type
        self.msg = msg
        self.error = error
        self.bs = bs
        self.int_info = int_info

    @staticmethod
    def recv(sock):
        # rsp_header_size = sock.recv(4, socket.MSG_WAITALL)
        rsp_header_size = _recv_message_in_len(sock, 4)
        rsp_header_size = struct.unpack(">i", rsp_header_size)[0]
        # rsp_header = sock.recv(rsp_header_size, socket.MSG_WAITALL)
        rsp_header = _recv_message_in_len(sock, rsp_header_size)

        xml_root = ET.fromstring(rsp_header)
        msg_type = xml_root.find('type').text
        msg_len = int(xml_root.find('msgLen').text)
        err_len = int(xml_root.find('errorLen').text)
        bs_len = int(xml_root.find('bsLen').text)
        int_info = int(xml_root.find('intInfo').text)

        # message = sock.recv(msg_len, socket.MSG_WAITALL) if msg_len != 0 else
        # None
        message = _recv_message_in_len(sock, msg_len) if msg_len != 0 else None
        # error = sock.recv(err_len, socket.MSG_WAITALL) if err_len != 0 else
        # None
        error = _recv_message_in_len(sock, err_len) if err_len != 0 else None
        # bs = sock.recv(bs_len, socket.MSG_WAITALL) if bs_len != 0 else None
        bs = _recv_message_in_len(sock, bs_len) if bs_len != 0 else None

        # if message:
        #     logger.debug(message)

        return iRODSMessage(msg_type, message, error, bs, int_info)

    @staticmethod
    def recv_into(sock, buffer):
        rsp_header_size = _recv_message_in_len(sock, 4)
        rsp_header_size = struct.unpack(">i", rsp_header_size)[0]
        rsp_header = _recv_message_in_len(sock, rsp_header_size)

        xml_root = ET.fromstring(rsp_header)
        msg_type = xml_root.find('type').text
        msg_len = int(xml_root.find('msgLen').text)
        err_len = int(xml_root.find('errorLen').text)
        bs_len = int(xml_root.find('bsLen').text)
        int_info = int(xml_root.find('intInfo').text)

        message = _recv_message_in_len(sock, msg_len) if msg_len != 0 else None
        error = _recv_message_in_len(sock, err_len) if err_len != 0 else None
        bs = _recv_message_into(sock, buffer, bs_len) if bs_len != 0 else None

        return iRODSMessage(msg_type, message, error, bs, int_info)


    @staticmethod
    def encode_unicode(my_str):
        if isinstance(my_str, UNICODE):
            return my_str.encode('utf-8')
        else:
            return my_str


    @staticmethod
    def pack_header(type, msg_len, err_len, bs_len, int_info):
        msg_header = ("<MsgHeader_PI>"
                      "<type>{}</type>"
                      "<msgLen>{}</msgLen>"
                      "<errorLen>{}</errorLen>"
                      "<bsLen>{}</bsLen>"
                      "<intInfo>{}</intInfo>"
                      "</MsgHeader_PI>").format(type, msg_len, err_len, bs_len, int_info)

        # encode if needed
        msg_header = iRODSMessage.encode_unicode(msg_header)

        # pack length
        msg_header_length = struct.pack(">i", len(msg_header))

        return msg_header_length + msg_header


    def pack(self):
        # pack main message and endcode if needed
        if self.msg:
            main_msg = self.encode_unicode(self.msg.pack())
        else:
            main_msg = b''

        # encode message parts if needed
        self.error = self.encode_unicode(self.error)
        self.bs = self.encode_unicode(self.bs)

        # pack header
        packed_header = self.pack_header(self.msg_type,
                                         len(main_msg),
                                         len(self.error),
                                         len(self.bs),
                                         self.int_info)

        return packed_header + main_msg + self.error + self.bs


    def get_main_message(self, cls):
        msg = cls()
        logger.debug(self.msg)
        msg.unpack(ET.fromstring(self.msg))
        return msg


#define CS_NEG_PI "int status; str result[MAX_NAME_LEN];"
class ClientServerNegotiation(Message):
    _name = 'CS_NEG_PI'
    status = IntegerProperty()
    result = StringProperty()


# define StartupPack_PI "int irodsProt; int reconnFlag; int connectCnt;
# str proxyUser[NAME_LEN]; str proxyRcatZone[NAME_LEN]; str
# clientUser[NAME_LEN]; str clientRcatZone[NAME_LEN]; str
# relVersion[NAME_LEN]; str apiVersion[NAME_LEN]; str option[NAME_LEN];"


class StartupPack(Message):
    _name = 'StartupPack_PI'

    def __init__(self, proxy_user, client_user, application_name = ''):
        super(StartupPack, self).__init__()
        if proxy_user and client_user:
            self.irodsProt = 1
            self.connectCnt = 0
            self.proxyUser, self.proxyRcatZone = proxy_user
            self.clientUser, self.clientRcatZone = client_user
            self.relVersion = "rods{}.{}.{}".format(*IRODS_VERSION)
            self.apiVersion = "{3}".format(*IRODS_VERSION)
            self.option = application_name

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

# define authResponseInp_PI "bin *response(RESPONSE_LEN); str *username;"


class AuthResponse(Message):
    _name = 'authResponseInp_PI'
    response = BinaryProperty(16)
    username = StringProperty()


class AuthChallenge(Message):
    _name = 'authRequestOut_PI'
    challenge = BinaryProperty(64)


class AuthPluginOut(Message):
    _name = 'authPlugReqOut_PI'
    result_ = StringProperty()
    # result_ = BinaryProperty(16)

# define InxIvalPair_PI "int iiLen; int *inx(iiLen); int *ivalue(iiLen);"


class BinBytesBuf(Message):
    _name = 'BinBytesBuf_PI'
    buflen = IntegerProperty()
    buf = BinaryProperty()


class PluginAuthMessage(Message):
    _name = 'authPlugReqInp_PI'
    auth_scheme_ = StringProperty()
    context_ = StringProperty()


class _OrderedMultiMapping :
    def keys(self):
        return self._keys
    def values(self):
        return self._values
    def __len__(self):
        return len(self._keys)
    def __init__(self, list_of_keyval_tuples ):
        self._keys = []
        self._values = []
        for k,v in list_of_keyval_tuples:
            self._keys.append(k)
            self._values.append(v)


class IntegerIntegerMap(Message):
    _name = 'InxIvalPair_PI'

    def __init__(self, data=None):
        super(IntegerIntegerMap, self).__init__()
        self.iiLen = 0
        if data:
            self.iiLen = len(data)
            self.inx = data.keys()
            self.ivalue = data.values()

    iiLen = IntegerProperty()
    inx = ArrayProperty(IntegerProperty())
    ivalue = ArrayProperty(IntegerProperty())

# define InxValPair_PI "int isLen; int *inx(isLen); str *svalue[isLen];"


class IntegerStringMap(Message):
    _name = 'InxValPair_PI'

    def __init__(self, data=None):
        super(IntegerStringMap, self).__init__()
        self.isLen = 0
        if data:
            self.isLen = len(data)
            self.inx = data.keys()
            self.svalue = data.values()

    isLen = IntegerProperty()
    inx = ArrayProperty(IntegerProperty())
    svalue = ArrayProperty(StringProperty())

# define KeyValPair_PI "int ssLen; str *keyWord[ssLen]; str *svalue[ssLen];"


class StringStringMap(Message):
    _name = 'KeyValPair_PI'

    def __init__(self, data=None):
        super(StringStringMap, self).__init__()
        self.ssLen = 0
        if data:
            self.ssLen = len(data)
            self.keyWord = data.keys()
            self.svalue = data.values()

    ssLen = IntegerProperty()
    keyWord = ArrayProperty(StringProperty())
    svalue = ArrayProperty(StringProperty())

# define GenQueryInp_PI "int maxRows; int continueInx; int
# partialStartIndex; int options; struct KeyValPair_PI; struct
# InxIvalPair_PI; struct InxValPair_PI;"


class GenQueryRequest(Message):
    _name = 'GenQueryInp_PI'
    maxRows = IntegerProperty()
    continueInx = IntegerProperty()
    partialStartIndex = IntegerProperty()
    options = IntegerProperty()
    KeyValPair_PI = SubmessageProperty(StringStringMap)
    InxIvalPair_PI = SubmessageProperty(IntegerIntegerMap)
    InxValPair_PI = SubmessageProperty(IntegerStringMap)

# define SqlResult_PI "int attriInx; int reslen; str *value(rowCnt)(reslen);"


class GenQueryResponseColumn(Message):
    _name = 'SqlResult_PI'
    attriInx = IntegerProperty()
    reslen = IntegerProperty()
    value = ArrayProperty(StringProperty())

# define GenQueryOut_PI "int rowCnt; int attriCnt; int continueInx; int
# totalRowCount; struct SqlResult_PI[MAX_SQL_ATTR];"


class GenQueryResponse(Message):
    _name = 'GenQueryOut_PI'
    rowCnt = IntegerProperty()
    attriCnt = IntegerProperty()
    continueInx = IntegerProperty()
    totalRowCount = IntegerProperty()
    SqlResult_PI = ArrayProperty(SubmessageProperty(GenQueryResponseColumn))

# define DataObjInp_PI "str objPath[MAX_NAME_LEN]; int createMode; int
# openFlags; double offset; double dataSize; int numThreads; int oprType;
# struct *SpecColl_PI; struct KeyValPair_PI;"


class FileOpenRequest(Message):
    _name = 'DataObjInp_PI'
    objPath = StringProperty()
    createMode = IntegerProperty()
    openFlags = IntegerProperty()
    offset = LongProperty()
    dataSize = LongProperty()
    numThreads = IntegerProperty()
    oprType = IntegerProperty()
    KeyValPair_PI = SubmessageProperty(StringStringMap)

# define OpenedDataObjInp_PI "int l1descInx; int len; int whence; int
# oprType; double offset; double bytesWritten; struct KeyValPair_PI;"


class OpenedDataObjRequest(Message):
    _name = 'OpenedDataObjInp_PI'
    l1descInx = IntegerProperty()
    len = IntegerProperty()
    whence = IntegerProperty()
    oprType = IntegerProperty()
    offset = LongProperty()
    bytesWritten = LongProperty()
    KeyValPair_PI = SubmessageProperty(StringStringMap)

# define fileLseekOut_PI "double offset;"


class FileSeekResponse(Message):
    _name = 'fileLseekOut_PI'
    offset = LongProperty()

# define DataObjCopyInp_PI "struct DataObjInp_PI; struct DataObjInp_PI;"


class ObjCopyRequest(Message):
    _name = 'DataObjCopyInp_PI'
    srcDataObjInp_PI = SubmessageProperty(FileOpenRequest)
    destDataObjInp_PI = SubmessageProperty(FileOpenRequest)

# define ModAVUMetadataInp_PI "str *arg0; str *arg1; str *arg2; str *arg3;
# str *arg4; str *arg5; str *arg6; str *arg7;  str *arg8;  str *arg9;"


class MetadataRequest(Message):
    _name = 'ModAVUMetadataInp_PI'

    def __init__(self, *args):
        super(MetadataRequest, self).__init__()
        for i in range(len(args)):
            if args[i]:
                setattr(self, 'arg%d' % i, args[i])

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

# define modAccessControlInp_PI "int recursiveFlag; str *accessLevel; str
# *userName; str *zone; str *path;"


class ModAclRequest(Message):
    _name = 'modAccessControlInp_PI'
    recursiveFlag = IntegerProperty()
    accessLevel = StringProperty()
    userName = StringProperty()
    zone = StringProperty()
    path = StringProperty()

# define CollInp_PI "str collName[MAX_NAME_LEN]; struct KeyValPair_PI;"


class CollectionRequest(Message):
    _name = 'CollInpNew_PI'
    collName = StringProperty()
    flags = IntegerProperty()
    oprType = IntegerProperty()
    KeyValPair_PI = SubmessageProperty(StringStringMap)

# define Version_PI "int status; str relVersion[NAME_LEN]; str
# apiVersion[NAME_LEN]; int reconnPort; str reconnAddr[LONG_NAME_LEN]; int
# cookie;"


class VersionResponse(Message):
    _name = 'Version_PI'
    status = IntegerProperty()
    relVersion = StringProperty()
    apiVersion = StringProperty()
    reconnPort = IntegerProperty()
    reconnAddr = StringProperty()
    cookie = IntegerProperty()


# define generalAdminInp_PI "str *arg0; str *arg1; str *arg2; str *arg3;
# str *arg4; str *arg5; str *arg6; str *arg7;  str *arg8;  str *arg9;"

class GeneralAdminRequest(Message):
    _name = 'generalAdminInp_PI'

    def __init__(self, *args):
        super(GeneralAdminRequest, self).__init__()
        for i in range(10):
            if i < len(args) and args[i]:
                setattr(self, 'arg{0}'.format(i), args[i])
            else:
                setattr(self, 'arg{0}'.format(i), '')

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


#define ticketAdminInp_PI "str *arg1; str *arg2; str *arg3; str *arg4; str *arg5; str *arg6;"

class TicketAdminRequest(Message):
    _name = 'ticketAdminInp_PI'

    def __init__(self, *args):
        super(TicketAdminRequest, self).__init__()
        for i in range(6):
            if i < len(args) and args[i]:
                setattr(self, 'arg{0}'.format(i+1), str(args[i]))
            else:
                setattr(self, 'arg{0}'.format(i+1), "")

    arg1 = StringProperty()
    arg2 = StringProperty()
    arg3 = StringProperty()
    arg4 = StringProperty()
    arg5 = StringProperty()
    arg6 = StringProperty()


#define specificQueryInp_PI "str *sql; str *arg1; str *arg2; str *arg3; str *arg4; str *arg5; str *arg6; str *arg7; str *arg8; str *arg9; str *arg10; int maxRows; int continueInx; int rowOffset; int options; struct KeyValPair_PI;"

class SpecificQueryRequest(Message):
    _name = 'specificQueryInp_PI'
    sql = StringProperty()

    arg1 = StringProperty()
    arg2 = StringProperty()
    arg3 = StringProperty()
    arg4 = StringProperty()
    arg5 = StringProperty()
    arg6 = StringProperty()
    arg7 = StringProperty()
    arg8 = StringProperty()
    arg9 = StringProperty()
    arg10 = StringProperty()

    maxRows = IntegerProperty()
    continueInx = IntegerProperty()
    rowOffset = IntegerProperty()
    options = IntegerProperty()
    KeyValPair_PI = SubmessageProperty(StringStringMap)


# define RHostAddr_PI "str hostAddr[LONG_NAME_LEN]; str
# rodsZone[NAME_LEN]; int port; int dummyInt;"

class RodsHostAddress(Message):
    _name = 'RHostAddr_PI'
    hostAddr = StringProperty()
    rodsZone = StringProperty()
    port = IntegerProperty()
    dummyInt = IntegerProperty()


# define MsParam_PI "str *label; piStr *type; ?type *inOutStruct; struct
# *BinBytesBuf_PI;"

class MsParam(Message):
    _name = 'MsParam_PI'
    label = StringProperty()
    type = StringProperty()

    # for packing
    inOutStruct = SubmessageProperty()
    BinBytesBuf_PI = SubmessageProperty(BinBytesBuf)

    # override Message.unpack() to unpack inOutStruct
    # depending on the received <type> element
    def unpack(self, root):
        for (name, prop) in self._ordered_properties:
            if name == 'inOutStruct':
                continue

            unpacked_value = prop.unpack(root.findall(name))
            self._values[name] = unpacked_value

            # type tells us what type of data structure we are unpacking
            # e.g: <type>ExecCmdOut_PI</type>
            if name == 'type':

                # unpack struct accordingly
                message_class = globals()[unpacked_value]
                self._values['inOutStruct'] = SubmessageProperty(
                    message_class).unpack(root.findall(unpacked_value))


# define MsParamArray_PI "int paramLen; int oprType; struct
# *MsParam_PI[paramLen];"

class MsParamArray(Message):
    _name = 'MsParamArray_PI'
    paramLen = IntegerProperty()
    oprType = IntegerProperty()
    MsParam_PI = ArrayProperty(SubmessageProperty(MsParam))


# define ExecMyRuleInp_PI "str myRule[META_STR_LEN]; struct RHostAddr_PI;
# struct KeyValPair_PI; str outParamDesc[LONG_NAME_LEN]; struct
# *MsParamArray_PI;"

class RuleExecutionRequest(Message):
    _name = 'ExecMyRuleInp_PI'
    myRule = StringProperty()
    addr = SubmessageProperty(RodsHostAddress)
    condInput = SubmessageProperty(StringStringMap)
    outParamDesc = StringProperty()
    inpParamArray = SubmessageProperty(MsParamArray)


# define ExecCmdOut_PI "struct BinBytesBuf_PI; struct BinBytesBuf_PI; int
# status;"

class ExecCmdOut_PI(Message):
    '''
    In this case the above class name must match the name
    of its root element to be unpacked dynamically,
    since it is one of the possible types for MsParam.
    '''
    _name = 'ExecCmdOut_PI'

    # for packing
    stdoutBuf = SubmessageProperty(BinBytesBuf)
    stderrBuf = SubmessageProperty(BinBytesBuf)

    status = IntegerProperty()

    # need custom unpacking since both buffers have the same element name
    def unpack(self, root):
        for (name, prop) in self._ordered_properties:
            if name == 'stdoutBuf':
                unpacked_value = prop.unpack(
                    root.findall(prop.message_cls._name)[:1])

            elif name == 'stderrBuf':
                unpacked_value = prop.unpack(
                    root.findall(prop.message_cls._name)[1:])

            else:
                unpacked_value = prop.unpack(root.findall(name))

            self._values[name] = unpacked_value


# define STR_PI "str myStr;"

class STR_PI(Message):
    '''
    Another "returnable" MsParam type
    '''
    _name = 'STR_PI'
    myStr = StringProperty()


class DataObjInfo(Message):
    _name = 'DataObjInfo_PI'
    objPath = StringProperty()
    rescName = StringProperty()
    rescHier = StringProperty()
    dataType = StringProperty()
    dataSize = LongProperty()
    chksum = StringProperty()
    version = StringProperty()
    filePath = StringProperty()
    dataOwnerName = StringProperty()
    dataOwnerZone = StringProperty()
    replNum = IntegerProperty()
    replStatus = IntegerProperty()
    statusString = StringProperty()
    dataId = LongProperty()
    collId = LongProperty()
    dataMapId = IntegerProperty()
    dataComments = StringProperty()
    dataMode = StringProperty()
    dataExpiry = StringProperty()
    dataCreate = StringProperty()
    dataModify = StringProperty()
    dataAccess = StringProperty()
    dataAccessInx = IntegerProperty()
    writeFlag = IntegerProperty()
    destRescName = StringProperty()
    backupRescName = StringProperty()
    subPath = StringProperty()
    specColl = IntegerProperty()
    regUid = IntegerProperty()
    otherFlags = IntegerProperty()
    KeyValPair_PI = SubmessageProperty(StringStringMap)
    in_pdmo = StringProperty()
    next = IntegerProperty()
    rescId = LongProperty()

class ModDataObjMeta(Message):
    _name = "ModDataObjMeta_PI"
    dataObjInfo = SubmessageProperty(DataObjInfo)
    regParam = SubmessageProperty(StringStringMap)

#define RErrMsg_PI "int status; str msg[ERR_MSG_LEN];"

class ErrorMessage(Message):
    _name = 'RErrMsg_PI'
    status = IntegerProperty()
    msg = StringProperty()


#define RError_PI "int count; struct *RErrMsg_PI[count];"

class Error(Message):
    _name = 'RError_PI'
    count = IntegerProperty()
    RErrMsg_PI = ArrayProperty(SubmessageProperty(ErrorMessage))


def empty_gen_query_out(cols):
    sql_results = [GenQueryResponseColumn(attriInx=col.icat_id, value=[])
                   for col in cols]
    gqo = GenQueryResponse(
        rowCnt=0,
        attriCnt=len(cols),
        SqlResult_PI=sql_results
    )
    return gqo
