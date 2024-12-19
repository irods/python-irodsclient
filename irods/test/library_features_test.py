#! /usr/bin/env python

import os
import sys
import unittest

import irods.test.helpers as helpers


class TestLibraryFeatures(unittest.TestCase):

    def setUp(self):
        self.sess = helpers.make_session()

    def tearDown(self):
        """Close connections."""
        self.sess.cleanup()

    def test_library_features__issue_556(self):
        if self.sess.server_version < (4, 3, 1):
            self.skipTest("Do not test library features before iRODS 4.3.1")

        features = self.sess.library_features()

        # Test that returned features are in the form of a Python dict object.
        self.assertIsInstance(features, dict)

        # Test that features is populated by at least one item.
        self.assertTrue(features)


if __name__ == "__main__":
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath("../.."))
    unittest.main()
