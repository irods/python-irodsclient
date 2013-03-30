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

    def test_inx_ival_pair(self):
        iip = InxIvalPair()
        iip.iiLen = 2
        iip.inx = [4,5]
        iip.ivalue = [1,2]
        expected = "<InxIvalPair_PI>\
<iiLen>2</iiLen>\
<inx>4</inx>\
<inx>5</inx>\
<ivalue>1</ivalue>\
<ivalue>2</ivalue>\
</InxIvalPair_PI>"
        self.assertEqual(iip.pack(), expected)

        iip2 = InxIvalPair()
        iip2.unpack(ET.fromstring(expected))
        self.assertEqual(iip2.iiLen, 2)
        self.assertEqual(iip2.inx, [4,5])
        self.assertEqual(iip2.ivalue, [1,2])

    def test_key_val_pair(self):
        kvp = KeyValPair()
        kvp.ssLen = 2
        kvp.keyWord = ["one", "two"]
        kvp.svalue = ["three", "four"]
        expected = "<KeyValPair_PI>\
<ssLen>2</ssLen>\
<keyWord>one</keyWord>\
<keyWord>two</keyWord>\
<svalue>three</svalue>\
<svalue>four</svalue>\
</KeyValPair_PI>"
        self.assertEqual(kvp.pack(), expected)

        kvp2 = KeyValPair()
        kvp2.unpack(ET.fromstring(expected))
        self.assertEqual(kvp2.ssLen, 2)
        self.assertEqual(kvp2.keyWord, ["one", "two"])
        self.assertEqual(kvp2.svalue, ["three", "four"])

    def test_gen_query_inp(self):
        gq = GenQueryInp()
        gq.maxRows = 4
        gq.continueInx = 3
        gq.partialStartIndex = 2
        gq.options = 1
        gq.KeyValPair = KeyValPair(ssLen=2, keyWord=["one", "two"], svalue=["three", "four"])
        gq.InxIvalPair = InxIvalPair(iiLen=2, inx=[4,5], ivalue=[1,2])
        gq.InxValPair = InxValPair(isLen=2, inx=[1,2], svalue=["five", "six"])

        expected = "<GenQueryInp_PI><maxRows>4</maxRows><continueInx>3</continueInx><partialStartIndex>2</partialStartIndex><options>1</options><KeyValPair_PI><ssLen>2</ssLen><keyWord>one</keyWord><keyWord>two</keyWord><svalue>three</svalue><svalue>four</svalue></KeyValPair_PI><InxIvalPair_PI><iiLen>2</iiLen><inx>4</inx><inx>5</inx><ivalue>1</ivalue><ivalue>2</ivalue></InxIvalPair_PI><InxValPair_PI><isLen>2</isLen><inx>1</inx><inx>2</inx><svalue>five</svalue><svalue>six</svalue></InxValPair_PI></GenQueryInp_PI>"
        self.assertEqual(gq.pack(), expected)

        gq2 = GenQueryInp()
        gq2.unpack(ET.fromstring(expected))
        self.assertEqual(gq2.maxRows, 4)
        self.assertEqual(gq2.continueInx, 3)
        self.assertEqual(gq2.partialStartIndex, 2)
        self.assertEqual(gq2.options, 1)

        self.assertEqual(gq2.KeyValPair.ssLen, 2)
        self.assertEqual(gq2.KeyValPair.keyWord, ["one", "two"])
        self.assertEqual(gq2.KeyValPair.svalue, ["three", "four"])

        self.assertEqual(gq2.InxIvalPair.iiLen, 2)
        self.assertEqual(gq2.InxIvalPair.inx, [4,5])
        self.assertEqual(gq2.InxIvalPair.ivalue, [1,2])

        self.assertEqual(gq2.InxValPair.isLen, 2)
        self.assertEqual(gq2.InxValPair.inx, [1,2])
        self.assertEqual(gq2.InxValPair.svalue, ["five","six"])

        self.assertEqual(gq2.pack(), expected)

if __name__ == "__main__":
    unittest.main()
