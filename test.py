#!/usr/bin/env python
import unittest
from irods.message import StartupPack, AuthResponseInp, InxIvalPair, \
InxValPair, KeyValPair, GenQueryInp, SqlResult, GenQueryOut

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
        sup.option = 4
        xml_str = sup.pack()
        print xml_str
        expected_xml = "hello"
        self.assertEqual(xml_str, expected_xml)

if __name__ == "__main__":
    unittest.main()
