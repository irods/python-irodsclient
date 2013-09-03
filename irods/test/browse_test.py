#!/usr/bin/env python
import os
import sys
import unittest


class TestMessages(unittest.TestCase):

    def setUp(self):
        from irods.session import iRODSSession
        import config

        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)

    def test_get_collection(self):
        path = "/tempZone/home/rods"
        coll = self.sess.get_collection(path)
        self.assertEquals(path, coll.path)

        new_coll = self.sess.create_collection("/tempZone/home/rods/test_dir")
        self.assertEquals(new_coll.name, 'test_dir')


if __name__ == "__main__":
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
