#!/usr/bin/env python

# unit test for miscsvrinfo.py

import os
import sys
import unittest
import irods.test.config  as config
import time

from irods.miscsvrinfo import iMiscSvrInfo

class TestMiscSvrInfo(unittest.TestCase):
    
    def setUp(self):
        self.m = iMiscSvrInfo(config.IRODS_SERVER_HOST)

    def testServerType(self):
        self.assertTrue(self.m.serverType == "RCAT_ENABLED")
    
    def testRelVersion(self):
        relString = "rods" + ".".join([str(x) for x in config.IRODS_SERVER_VERSION])
        self.assertTrue(self.m.relVersion == relString)

    def testRodsZone(self):
        self.assertTrue(self.m.rodsZone   == config.IRODS_SERVER_ZONE)

    def testServerBootTime(self):
        curr =  int(time.time())
        self.assertTrue(self.m.serverBootTime > 0 and self.m.serverBootTime < curr)

    def testApiVersion(self):
        self.assertTrue(self.m.apiVersion == config.IRODS_API_VERSION)


if __name__ == '__main__':
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
