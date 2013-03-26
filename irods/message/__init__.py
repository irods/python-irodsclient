import xml.etree.ElementTree as ET
from message import Message
from property import BinaryProperty, StringProperty

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
        rsp_header = sock.recv(rsp_header_size)
        logging.debug(rsp_header)
            
        xml_root = ET.fromstring(rsp_header)
        type = xml_root.find('type').text
        msg_len = int(xml_root.find('msgLen').text)
        err_len = int(xml_root.find('errorLen').text)
        bs_len = int(xml_root.find('bsLen').text)
        int_info = int(xml_root.find('intInfo').text)

        message = sock.recv(msg_len) if msg_len != 0 else None
        error = sock.recv(err_len) if err_len != 0 else None
        bs = sock.recv(bs_len) if bs_len != 0 else None
    
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

#define authResponseInp_PI "bin *response(RESPONSE_LEN); str *username;"
class AuthResponseInp(Message):
    response = BinaryProperty(16)
    username = StringProperty()
