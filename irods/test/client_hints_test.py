#!/usr/bin/env python

import os
import sys
import unittest

import irods.test.helpers as helpers


class TestClientHints(unittest.TestCase):

    def setUp(self):
        self.sess = helpers.make_session()

    def tearDown(self):
        """Close connections."""
        self.sess.cleanup()

    def test_client_hints(self):
        client_hints = self.sess.client_hints

        self.assertIn("specific_queries", client_hints)
        self.assertIn("rules", client_hints)
        self.assertIn("plugins", client_hints)
        self.assertIn("hash_scheme", client_hints)
        self.assertIn("match_hash_policy", client_hints)


if __name__ == "__main__":
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath("../.."))
    unittest.main()
