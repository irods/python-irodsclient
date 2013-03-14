import struct
import xml.etree.ElementTree as ET

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
		print rsp_header
			
		xml_root = ET.fromstring(rsp_header)
		type = xml_root.find('type').text
		msg_len = int(xml_root.find('msgLen').text)
		err_len = int(xml_root.find('errorLen').text)
		bs_len = int(xml_root.find('bsLen').text)
		int_info = int(xml_root.find('intInfo').text)

		message = sock.recv(msg_len) if msg_len != 0 else None
		error = sock.recv(err_len) if err_len != 0 else None
		bs = sock.recv(bs_len) if bs_len != 0 else None

		return iRODSMessage(type, message, error, bs, int_info)

	def pack(self):
		msg_header = "<MsgHeader_PI><type>%s</type><msgLen>%d</msgLen><errorLen>%d</errorLen><bsLen>%d</bsLen><intInfo>%d</intInfo></MsgHeader_PI>" % (self.type, len(self.msg) if self.msg else 0, len(self.error) if self.error else 0, len(self.bs) if self.bs else 0, self.int_info if self.int_info else 0)
		msg_header_length = struct.pack(">i", len(msg_header))
		parts = [x for x in [self.msg, self.error, self.bs] if x is not None]
		msg = msg_header_length + msg_header + "".join(parts)
		return msg

class StartupMessage(object):
	def __init__(self, user=None, zone=None):
		self.user = user
		self.zone = zone

	def pack(self):
		str = """<StartupPack_PI>
		<irodsProt>0</irodsProt>
		<connectCnt>0</connectCnt>
		<proxyUser>%s</proxyUser>
		<proxyRcatZone>%s</proxyRcatZone>
		<clientUser>%s</clientUser>
		<clientRcatZone>%s</clientRcatZone>
		<relVersion>rods3.2</relVersion>
		<apiVersion>d</apiVersion>
		<option></option>
		</StartupPack_PI>""" % (self.user, self.zone, self.user, self.zone)
		return str
