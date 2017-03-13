#!/usr/bin/env python

# unit test for miscsvrinfo.py

import os
import sys
import unittest
import irods.test.config  as config

from irods.miscsvrinfo import iMiscSvrInfo

class TestMiscSvrInfo(unittest.TestCase):
    ###
    def setUp(self):
        self.m = iMiscSvrInfo(config.IRODS_SERVER_HOST)

    def testObjectFields(self):
        self.assertTrue(self.m.serverType == "RCAT_ENABLED")
        relString = "rods" + ".".join(map(str,config.IRODS_SERVER_VERSION))
        self.assertTrue(self.m.relVersion == relString)
        self.assertTrue(self.m.rodsZone   == config.IRODS_SERVER_ZONE)
        
        #test uptime?
        #test apiVersion?

        #test update function??

if __name__ == '__main__':
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
