#! /usr/bin/env python

from datetime import datetime
import errno
import os
import sys
import unittest
import irods.test.helpers as helpers
import irods.exception


class TestException(unittest.TestCase):

    def setUp(self):
        # open the session (per-test)
        self.sess = helpers.make_session()

    def tearDown(self):
        # close the session (per-test)
        self.sess.cleanup()

    def test_400(self):
        ses = self.sess
        data = ""
        try:
            seed = helpers.my_function_name() + ":" + str(datetime.now())
            data = (
                helpers.home_collection(ses) + "/" + helpers.unique_name(seed, "data")
            )
            exc = None
            with helpers.create_simple_resc(self, vault_path="/home") as resc_name:
                try:
                    # iRODS will attempt to make a data object where it doesn't have permission
                    ses.data_objects.create(data, resource=resc_name)
                except Exception as e:
                    exc = e
            self.assertIsNotNone(
                exc,
                "Creating data object in unwriteable vault did not raise an error as it should.",
            )
            excep_repr = repr(exc)
            errno_object = irods.exception.Errno(errno.EACCES)
            errno_repr = repr(errno_object)
            self.assertRegexpMatches(errno_repr, r"\bErrno\b")
            self.assertRegexpMatches(
                errno_repr, """['"]{msg}['"]""".format(msg=os.strerror(errno.EACCES))
            )
            self.assertIn(errno_repr, excep_repr)
        finally:
            if ses.data_objects.exists(data):
                ses.data_objects.unlink(data, force=True)


if __name__ == "__main__":
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath("../.."))
    unittest.main()
