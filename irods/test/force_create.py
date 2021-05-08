#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import unittest

from irods.exception import OVERWRITE_WITHOUT_FORCE_FLAG
import irods.test.helpers as helpers

class TestForceCreate(unittest.TestCase):

    def setUp(self):
        self.sess = helpers.make_session()

    def tearDown(self):
        """Close connections."""
        self.sess.cleanup()

    # This test should pass whether or not federation is configured:
    def test_force_create(self):
        if self.sess.server_version > (4, 2, 8):
            self.skipTest('force flag unneeded for create in iRODS > 4.2.8')
        session = self.sess
        FILE = '/{session.zone}/home/{session.username}/a.txt'.format(**locals())
        try:
            session.data_objects.unlink(FILE)
        except:
            pass
        error = None
        try:
            session.data_objects.create(FILE)
            session.data_objects.create(FILE)
        except OVERWRITE_WITHOUT_FORCE_FLAG:
            error = "OVERWRITE_WITHOUT_FORCE_FLAG"
        self.assertEqual (error, "OVERWRITE_WITHOUT_FORCE_FLAG")
        error = None
        try:
            session.data_objects.create(FILE, force=True)
        except:
            error = "Error creating with force"
        self.assertEqual (error, None)
        try:
            session.data_objects.unlink(FILE)
        except:
            error = "Error cleaning up"
        self.assertEqual (error, None)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
