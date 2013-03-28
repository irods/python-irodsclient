#!/usr/bin/env python
import unittest
from xml.etree import ElementTree as ET
from base64 import b64encode, b64decode
from irods.message import StartupPack, AuthResponseInp, InxIvalPair, \
InxValPair, KeyValPair, GenQueryInp, SqlResult

class TestMessages(unittest.TestCase):
    
    def test_startup_pack(self):
        sup = StartupPack()
        sup.irodsProt = 2
        sup.reconnFlag = 3
        sup.proxyUser = "rods"
        sup.proxyRcatZone = "tempZone"
        sup.clientUser = "rods"
        sup.clientRcatZone = "yoyoyo"
        sup.relVersion = "irods3.2"
        sup.apiVersion = "d"
        sup.option = "hellO"
        xml_str = sup.pack()
        expected = "<StartupPack_PI>\
<irodsProt>2</irodsProt>\
<reconnFlag>3</reconnFlag>\
<proxyUser>rods</proxyUser>\
<proxyRcatZone>tempZone</proxyRcatZone>\
<clientUser>rods</clientUser>\
<clientRcatZone>yoyoyo</clientRcatZone>\
<relVersion>irods3.2</relVersion>\
<apiVersion>d</apiVersion>\
<option>hellO</option>\
</StartupPack_PI>"
        self.assertEqual(xml_str, expected)

        sup2 = StartupPack()
        sup2.unpack(ET.fromstring(expected))
        self.assertEqual(sup2.irodsProt, 2)
        self.assertEqual(sup2.reconnFlag, 3)
        self.assertEqual(sup2.proxyUser, "rods")
        self.assertEqual(sup2.proxyRcatZone, "tempZone")
        self.assertEqual(sup2.clientUser, "rods")
        self.assertEqual(sup2.clientRcatZone, "yoyoyo")
        self.assertEqual(sup2.relVersion, "irods3.2")
        self.assertEqual(sup2.apiVersion, "d")
        self.assertEqual(sup2.option, "hellO")

    def test_auth_response(self):
        ar = AuthResponseInp()
        ar.response = "hello"
        ar.username = "rods"
        expected = "<AuthResponseInp_PI>\
<response>aGVsbG8=</response>\
<username>rods</username>\
</AuthResponseInp_PI>"
        self.assertEqual(ar.pack(), expected)

        ar2 = AuthResponseInp()
        ar2.unpack(ET.fromstring(expected))
        self.assertEqual(ar2.response, "hello")
        self.assertEqual(ar2.username, "rods")

if __name__ == "__main__":
    unittest.main()
