#! /usr/bin/env python
import os
import sys
if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest
from irods.session import iRODSSession
import irods.test.config as config


class TestConnections(unittest.TestCase):

    def setUp(self):
        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,  # 4444: why?
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)

    def tearDown(self):
        '''Close connections
        '''
        self.sess.cleanup()

    def test_connection(self):
        """
        @TODO: what does get_collection return?
        There should be a better way to test this...
        Wouldn't the iRODSSession init establish the connection?
        """
        coll = self.sess.collections.get('/{0}/home/{1}'.format(
            config.IRODS_SERVER_ZONE, config.IRODS_USER_USERNAME))
        self.assertTrue(coll, "Connection failed.")

    @unittest.skip("unimplemented")
    def test_failed_connection(self):
        """ Test the exception raised by a failed connection """
        # self.assertRaises()  How to fuddle the config.* to ensure setUp()
        #                     fails in connecting?
        pass

if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
