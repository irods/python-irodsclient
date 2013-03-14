#! /usr/bin/env python2.6
import socket
import struct
import xml.etree.ElementTree as ET
#from base64 import b64encode, b64decode
import hashlib

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("localhost", 4444))

# establish connection
main_message = "<StartupPack_PI><irodsProt>0</irodsProt><connectCnt>0</connectCnt><proxyUser>rods</proxyUser><proxyRcatZone>tempZone</proxyRcatZone><clientUser>rods</clientUser><clientRcatZone>tempZone</clientRcatZone><relVersion>rods3.2</relVersion><apiVersion>d</apiVersion><option></option></StartupPack_PI>"
msg_header = "<MsgHeader_PI><type>RODS_CONNECT</type><msgLen>%d</msgLen><errorLen>0</errorLen><bsLen>0</bsLen><intInfo>0</intInfo></MsgHeader_PI>" % len(main_message)
msg_header_length = struct.pack(">i", len(msg_header))
msg = msg_header_length + msg_header + main_message
print(msg)
print "-----------------"
sent = s.send(msg)

# header
# version_PI
class iRODSMessage(object):
	def __init__(self, type=None, msg=None, error=None, bs=None, int_info=None):
		self.type = type
		self.msg = msg
		self.error = error
		self.bs = bs
		self.int_info = int_info

	@staticmethod
	def recv(sock):
		rsp_header_size = s.recv(4)
		rsp_header_size = struct.unpack(">i", rsp_header_size)[0]
		rsp_header = s.recv(rsp_header_size)
		print rsp_header
			
		xml_root = ET.fromstring(rsp_header)
		type = xml_root.find('type').text
		msg_len = int(xml_root.find('msgLen').text)
		err_len = int(xml_root.find('errorLen').text)
		bs_len = int(xml_root.find('bsLen').text)
		int_info = int(xml_root.find('intInfo').text)

		message = s.recv(msg_len) if msg_len != 0 else None
		error = s.recv(err_len) if err_len != 0 else None
		bs = s.recv(bs_len) if bs_len != 0 else None

		return iRODSMessage(type, message, error, bs, int_info)

	def pack(self):
		msg_header = "<MsgHeader_PI><type>%s</type><msgLen>%d</msgLen><errorLen>%d</errorLen><bsLen>%d</bsLen><intInfo>%d</intInfo></MsgHeader_PI>" % (self.type, len(self.msg) if self.msg else 0, len(self.error) if self.error else 0, len(self.bs) if self.bs else 0, self.int_info if self.int_info else 0)
		msg_header_length = struct.pack(">i", len(msg_header))
		parts = [x for x in [self.msg, self.error, self.bs] if x is not None]
		msg = msg_header_length + msg_header + "".join(parts)
		return msg

vesion_msg = iRODSMessage.recv(s)

# authenticate
auth_req = iRODSMessage(type='RODS_API_REQ', int_info=703)
print auth_req.pack()
sent = s.send(auth_req.pack())

# challenge
challenge = iRODSMessage.recv(s)
response_len = 16
max_pwd_len = 50
padded_pwd = struct.pack("50s", "rods")
m = hashlib.md5()
m.update(challenge.msg)
m.update(padded_pwd)
encoded_pwd = m.digest()

encoded_pwd = encoded_pwd.replace('\x00', '\x01')
pwd_msg = encoded_pwd + 'rods' + '\x00'
pwd_request = iRODSMessage(type='RODS_API_REQ', int_info=704, msg=pwd_msg)
s.send(pwd_request.pack())

auth_response = iRODSMessage.recv(s)
if not auth_response.error:
	print "Successful login"

#disconnect
disconnect_msg = iRODSMessage(type='RODS_DISCONNECT')
s.send(disconnect_msg.pack())
s.close()
