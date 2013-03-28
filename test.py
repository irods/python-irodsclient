#!/usr/bin/env python
import unittest
from irods.message import StartupPack, AuthResponseInp, InxIvalPair, \
InxValPair, KeyValPair, GenQueryInp, SqlResult
from xml.etree import ElementTree as ET

class TestMessages(unittest.TestCase):
    
    def test_startup_pack(self):
        sup =  StartupPack()
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
        self.assertEquals(sup2.irodsProt, 2)
        self.assertEquals(sup2.reconnFlag, 3)
        self.assertEquals(sup2.proxyUser, "rods")
        self.assertEquals(sup2.proxyRcatZone, "tempZone")
        self.assertEquals(sup2.clientUser, "rods")
        self.assertEquals(sup2.clientRcatZone, "yoyoyo")
        self.assertEquals(sup2.relVersion, "irods3.2")
        self.assertEquals(sup2.apiVersion, "d")
        self.assertEquals(sup2.option, "hellO")

if __name__ == "__main__":
    unittest.main()
