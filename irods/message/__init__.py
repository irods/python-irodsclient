"""Define objects related to communication with iRODS server API endpoints."""

import sys
import struct
import logging
import socket
import json
from six.moves import builtins
import irods.exception as ex
import xml.etree.ElementTree as ET_xml
import defusedxml.ElementTree as ET_secure_xml
from . import quasixml as ET_quasi_xml
from collections import namedtuple
import os
import fcntl
import ast
import threading
from irods.message.message import Message
from irods.message.property import (BinaryProperty, StringProperty,
                                    IntegerProperty, LongProperty, ArrayProperty,
                                    SubmessageProperty)

_TUPLE_LIKE_TYPES = (tuple, list)

def _qxml_server_version( var ):
    val = os.environ.get( var, '()' )
    vsn = (val and ast.literal_eval( val ))
    if not isinstance( vsn, _TUPLE_LIKE_TYPES ): return None
    return tuple( vsn )

if sys.version_info >= (3,):
    import enum
    class XML_Parser_Type(enum.Enum):
        _invalid = 0
        STANDARD_XML = 1
        QUASI_XML = 2
        SECURE_XML = 3
else:
    class MyIntEnum(int):
        """An integer enum class suited to the purpose. A shim until we get rid of Python2."""
        def __init__(self,i):
            """Initialize based on an integer or another instance."""
            super(MyIntEnum,self).__init__()
            try:self.i = i._value()
            except AttributeError:
                self.i = i
        def _value(self): return self.i
        @builtins.property
        def value(self): return self._value()

    class XML_Parser_Type(MyIntEnum):
        """An enum specifying which XML parser is active."""
        pass
    XML_Parser_Type.STANDARD_XML = XML_Parser_Type (1)
    XML_Parser_Type.QUASI_XML = XML_Parser_Type (2)
    XML_Parser_Type.SECURE_XML = XML_Parser_Type (3)

# We maintain values on a per-thread basis of:
#   - the server version with which we're communicating
#   - which of the choices of parser (STANDARD_XML or QUASI_XML) we're using

_thrlocal = threading.local()

# The packStruct message parser defaults to STANDARD_XML but we can override it by setting the
# environment variable PYTHON_IRODSCLIENT_DEFAULT_XML to either 'SECURE_XML' or 'QUASI_XML'.
# If QUASI_XML is selected, the environment variable PYTHON_IRODSCLIENT_QUASI_XML_SERVER_VERSION
# may also be set to a tuple "X,Y,Z" to inform the client of the connected iRODS server version.
# If we set a value for the version, it can be either:
#    * 4,2,8 to work with that server version and older ones which incorrectly encoded back-ticks as '&apos;'
#    * an empty tuple "()" or something >= 4,2,9 to work with newer servers to allow a flexible character
#      set within iRODS protocol.

class BadXMLSpec(RuntimeError): pass

_Quasi_Xml_Server_Version = _qxml_server_version('PYTHON_IRODSCLIENT_QUASI_XML_SERVER_VERSION')
if _Quasi_Xml_Server_Version is None:  # unspecified in environment yields empty tuple ()
    raise BadXMLSpec('Must properly specify a server version to use QUASI_XML')

_XML_strings = { k:v for k,v in vars(XML_Parser_Type).items() if k.endswith('_XML')}


_default_XML = os.environ.get('PYTHON_IRODSCLIENT_DEFAULT_XML','')
if not _default_XML:
    _default_XML = XML_Parser_Type.STANDARD_XML
else:
    try:
        _default_XML = _XML_strings[_default_XML]
    except KeyError:
        raise BadXMLSpec('XML parser type not recognized')


def current_XML_parser(get_module = False):
    d = getattr(_thrlocal,'xml_type',_default_XML)
    return d if not get_module else _XML_parsers[d]

def default_XML_parser(get_module = False):
    d = _default_XML
    return d if not get_module else _XML_parsers[d]

_XML_parsers = {
    XML_Parser_Type.STANDARD_XML : ET_xml,
    XML_Parser_Type.QUASI_XML : ET_quasi_xml,
    XML_Parser_Type.SECURE_XML : ET_secure_xml
}


def XML_entities_active():
    Server = getattr(_thrlocal,'irods_server_version',_Quasi_Xml_Server_Version)
    return [ ('&', '&amp;'), # note: order matters. & must be encoded first.
             ('<', '&lt;'),
             ('>', '&gt;'),
             ('"', '&quot;'),
             ("'" if not(Server) or Server >= (4,2,9) else '`',
               '&apos;') # https://github.com/irods/irods/issues/4132
            ]


# ET() [no-args form] will just fetch the current thread's XML parser settings

def ET(xml_type = 0, server_version = None):
    """
    Return the module used to parse XML from iRODS protocol messages text.

    May also be used to specify the following attributes of the currently running thread:

    `xml_type', if given, should be 1 for STANDARD_XML or 2 for QUASI_XML.
      * QUASI_XML is custom parser designed to be more compatible with the use of
        non-printable characters in object names.
      * STANDARD_XML uses the standard module, xml.etree.ElementTree.

    `server_version', if given, should be a list or tuple specifying the version of the connected iRODS server.

    """
    if xml_type is not 0:
        _thrlocal.xml_type = default_XML_parser() if xml_type in (None, XML_Parser_Type(0)) \
                        else XML_Parser_Type(xml_type)
    if isinstance(server_version, _TUPLE_LIKE_TYPES):
        _thrlocal.irods_server_version = tuple(server_version)  #  A default server version for Quasi-XML parsing is set (from the environment) and
    return _XML_parsers[current_XML_parser()]                   #  applies to all threads in which ET() has not been called to update the value.


logger = logging.getLogger(__name__)

IRODS_VERSION = (4, 3, 0, 'd')

try:
    # Python 2
    UNICODE = unicode
except NameError:
    # Python 3
    UNICODE = str



# Necessary for older python (<3.7):
_socket_is_blocking = (lambda self: 0 == fcntl.fcntl(self.fileno(), fcntl.F_GETFL) & os.O_NONBLOCK)

def _recv_message_in_len(sock, size):
    size_left = size
    retbuf = None

    # Get socket properties for debug and exception messages.
    host, port = sock.getpeername()
    is_blocking = _socket_is_blocking(sock)
    timeout = sock.gettimeout()

    logger.debug('host: %s',host)
    logger.debug('port: %d',port)
    logger.debug('is_blocking: %s',is_blocking)
    logger.debug('timeout: %s',timeout)

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

        # This prevents an infinite loop. If the call to recv()
        # returns an empty buffer, break out of the loop.
        if len(buf) == 0:
            break
        size_left -= len(buf)
        if retbuf is None:
            retbuf = buf
        else:
            retbuf += buf

    # This method is supposed to read and return 'size'
    # bytes from the socket. If it reads no bytes (retbuf
    # will be None), or if it reads less number of bytes
    # than 'size', throw a socket.error exception
    if retbuf is None or len(retbuf) != size:
        retbuf_size = len(retbuf) if retbuf is not None else 0
        msg = 'Read {} bytes from the socket (host {}, port {}) instead of expected {} bytes'.format(
               retbuf_size, host, port, size)
        raise socket.error(msg)

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

#------------------------------------

class BinBytesBuf(Message):
    _name = 'BinBytesBuf_PI'
    buflen = IntegerProperty()
    buf = BinaryProperty()

class JSON_Binary_Response(BinBytesBuf):
    pass

class iRODSMessage(object):

    class ResponseNotParseable(Exception):

        """
        Raised by get_main_message(ResponseClass) to indicate a server response
        wraps a msg string that is the `None' object rather than an XML String.
        (Not raised for the ResponseClass is irods.message.Error; see source of
        get_main_message for further detail.)
        """
        pass

    def __init__(self, msg_type=b'', msg=None, error=b'', bs=b'', int_info=0):
        self.msg_type = msg_type
        self.msg = msg
        self.error = error
        self.bs = bs
        self.int_info = int_info

    def get_json_encoded_struct (self):
        Xml = ET().fromstring(self.msg.replace(b'\0',b''))
        json_str = Xml.find('buf').text
        if Xml.tag == 'BinBytesBuf_PI':
            mybin = JSON_Binary_Response()
            mybin.unpack(Xml)
            json_str = mybin.buf.replace(b'\0',b'').decode()
        return json.loads( json_str )

    @staticmethod
    def recv(sock):
        # rsp_header_size = sock.recv(4, socket.MSG_WAITALL)
        rsp_header_size = _recv_message_in_len(sock, 4)
        rsp_header_size = struct.unpack(">i", rsp_header_size)[0]
        # rsp_header = sock.recv(rsp_header_size, socket.MSG_WAITALL)
        rsp_header = _recv_message_in_len(sock, rsp_header_size)

        xml_root = ET().fromstring(rsp_header)
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

        xml_root = ET().fromstring(rsp_header)
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


    def get_main_message(self, cls, r_error = None):
        msg = cls()
        logger.debug('Attempt to parse server response [%r] as class [%r].',self.msg,cls)
        if self.error and isinstance(r_error, RErrorStack):
            r_error.fill( iRODSMessage(msg=self.error).get_main_message(Error) )
        if self.msg is None:
            if cls is not Error:
                # - For dedicated API response classes being built from server response, allow catching
                #   of the exception.  However, let iRODS errors such as CAT_NO_ROWS_FOUND to filter
                #   through as usual for express reporting by instances of irods.connection.Connection .
                message = "Server response was {self.msg} while parsing as [{cls}]".format(**locals())
                raise self.ResponseNotParseable( message )
        msg.unpack(ET().fromstring(self.msg))
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


# The following PamAuthRequest* classes correspond to older, less generic
# PAM auth api in iRODS, but one which allowed longer password tokens.
# They are contributed by Rick van de Hoef at Utrecht Univ, c. June 2021:

class PamAuthRequest(Message):
    _name = 'pamAuthRequestInp_PI'
    pamUser = StringProperty()
    pamPassword = StringProperty()
    timeToLive = IntegerProperty()

class PamAuthRequestOut(Message):
    _name = 'pamAuthRequestOut_PI'
    irodsPamPassword = StringProperty()
    @builtins.property
    def result_(self): return self.irodsPamPassword



# define InxIvalPair_PI "int iiLen; int *inx(iiLen); int *ivalue(iiLen);"

class JSON_Binary_Request(BinBytesBuf):

    """A message body whose payload is BinBytesBuf containing JSON."""

    def __init__(self,msg_struct):
        """Initialize with a Python data structure that will be converted to JSON."""
        super(JSON_Binary_Request,self).__init__()
        string = json.dumps(msg_struct)
        self.buf = string
        self.buflen = len(string)

class BytesBuf(Message):

    """A generic structure carrying text content"""

    _name = 'BytesBuf_PI'
    buflen = IntegerProperty()
    buf = StringProperty()
    def __init__(self,string,*v,**kw):
        super(BytesBuf,self).__init__(*v,**kw)
        self.buf = string
        self.buflen = len(self.buf)

class JSON_XMLFramed_Request(BytesBuf):

    """A message body whose payload is a BytesBuf containing JSON."""
    def __init__(self, msg_struct):
        """Initialize with a Python data structure that will be converted to JSON."""
        s = json.dumps(msg_struct)
        super(JSON_XMLFramed_Request,self).__init__(s)

def JSON_Message( msg_struct , server_version = () ):
    cls = JSON_XMLFramed_Request if server_version < (4,2,9) \
          else JSON_Binary_Request
    return cls(msg_struct)


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

class DataObjChksumRequest(FileOpenRequest):
    """Report and/or generate a data object's checksum."""

    def __init__(self,path,**chksumOptions):
        """Construct the request using the path of a data object."""
        super(DataObjChksumRequest,self).__init__()
        for attr,prop in vars(FileOpenRequest).items():
            if isinstance(prop, (IntegerProperty,LongProperty)):
                setattr(self, attr, 0)
        self.objPath = path
        self.KeyValPair_PI = StringStringMap(chksumOptions)

class DataObjChksumResponse(Message):
    name = 'Str_PI'
    myStr = StringProperty()

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


class _admin_request_base(Message):

    _name = None

    def __init__(self, *args):
        if self.__class__._name is None:
            raise NotImplementedError
        super(_admin_request_base, self).__init__()
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


# define generalAdminInp_PI "str *arg0; str *arg1; str *arg2; str *arg3;
# str *arg4; str *arg5; str *arg6; str *arg7;  str *arg8;  str *arg9;"

class GeneralAdminRequest(_admin_request_base):
    _name = 'generalAdminInp_PI'


# define userAdminInp_PI "str *arg0; str *arg1; str *arg2; str *arg3;
# str *arg4; str *arg5; str *arg6; str *arg7;  str *arg8;  str *arg9;"

class UserAdminRequest(_admin_request_base):
    _name = 'userAdminInp_PI'


class GetTempPasswordForOtherRequest(Message):
    _name = 'getTempPasswordForOtherInp_PI'
    targetUser = StringProperty()
    unused = StringProperty()


class GetTempPasswordForOtherOut(Message):
    _name = 'getTempPasswordForOtherOut_PI'
    stringToHashWith = StringProperty()


class GetTempPasswordOut(Message):
    _name = 'getTempPasswordOut_PI'
    stringToHashWith = StringProperty()


#in iRODS <= 4.2.10:
#define ticketAdminInp_PI "str *arg1; str *arg2; str *arg3; str *arg4; str *arg5; str *arg6;"

#in iRODS <= 4.2.11:
#define ticketAdminInp_PI "str *arg1; str *arg2; str *arg3; str *arg4; str *arg5; str *arg6; struct KeyValPair_PI;"

def TicketAdminRequest(session):

    # class is different depending on server version

    SERVER_REQUIRES_KEYVAL_PAIRS = (session.server_version >= (4,2,11))

    class TicketAdminRequest_(Message):
        _name = 'ticketAdminInp_PI'

        def __init__(self, *args,**ticketOpts):
            super(TicketAdminRequest_, self).__init__()
            for i in range(6):
                if i < len(args) and args[i]:
                    setattr(self, 'arg{0}'.format(i+1), str(args[i]))
                else:
                    setattr(self, 'arg{0}'.format(i+1), "")
            if SERVER_REQUIRES_KEYVAL_PAIRS:
                self.KeyValPair_PI = StringStringMap(ticketOpts)

        arg1 = StringProperty()
        arg2 = StringProperty()
        arg3 = StringProperty()
        arg4 = StringProperty()
        arg5 = StringProperty()
        arg6 = StringProperty()

        if SERVER_REQUIRES_KEYVAL_PAIRS:
            KeyValPair_PI = SubmessageProperty(StringStringMap)

    return TicketAdminRequest_


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


#  -- A tuple-descended class which facilitates filling in a
#     quasi-RError stack from a JSON formatted list.

_Server_Status_Message = namedtuple('server_status_msg',('msg','status'))


class RErrorStack(list):

    """A list of returned RErrors."""

    def __init__(self,Err = None):
        """Initialize from the `errors' member of an API return message."""
        super(RErrorStack,self).__init__() # 'list' class initialization
        self.fill(Err)

    def fill(self,Err = None):

        # first, we try to parse from a JSON list, as this is how message and status return the Data.chksum call.
        if isinstance (Err, (tuple,list)):
            self[:] = [ RError( _Server_Status_Message( msg = elem["message"],
                                                        status = elem["error_code"] )
                               ) for elem in Err
                       ]
            return

        # next, we try to parse from a a response message - eg. as returned by the Rule.execute API call when a rule fails.
        if Err is not None:
            self[:] = [ RError(Err.RErrMsg_PI[i]) for i in range(Err.count) ]


class RError(object):

    """One of a list of RError messages potentially returned to the client
       from an iRODS API call.  """

    Encoding = 'utf-8'

    def __init__(self,entry):
        """Initialize from one member of the RErrMsg_PI array."""
        super(RError,self).__init__()
        self.raw_msg_ = entry.msg
        self.status_ = entry.status


    @builtins.property
    def message(self): #return self.raw_msg_.decode(self.Encoding)
        msg_ = self.raw_msg_
        if type(msg_) is UNICODE:
            return msg_
        elif type(msg_) is bytes:
            return msg_.decode(self.Encoding)
        else:
            raise RuntimeError('bad msg type in',msg_)

    @builtins.property
    def status(self): return int(self.status_)


    @builtins.property
    def status_str(self):
        """Retrieve the IRODS error identifier."""
        return ex.get_exception_class_by_code( self.status, name_only=True )


    def __str__(self):
        """Retrieve the error message text."""
        return self.message

    def __int__(self):
        """Retrieve integer error code."""
        return self.status

    def __repr__(self):
        """Show both the message and iRODS error type (both integer and human-readable)."""
        return "{self.__class__.__name__}"\
               "<message = {self.message!r}, status = {self.status} {self.status_str}>".format(**locals())


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
