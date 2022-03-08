#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import unittest
from irods.exception import NetworkException
import irods.test.helpers as helpers


class TestConnections(unittest.TestCase):

    def setUp(self):
        self.sess = helpers.make_session()

    def tearDown(self):
        '''Close connections
        '''
        self.sess.cleanup()

    def test_connection(self):
        with self.sess.pool.get_connection() as conn:
            self.assertTrue(conn)

    def test_connection_destructor(self):
        conn = self.sess.pool.get_connection()
        conn.__del__()
        # These asserts confirm that disconnect() in connection destructor is called
        self.assertIsNone(conn.socket)
        self.assertTrue(conn._disconnected)
        conn.release(destroy=True)

    def test_failed_connection(self):
        # mess with the account's port
        saved_port = self.sess.port
        self.sess.pool.account.port = 6666

        # try connecting
        with self.assertRaises(NetworkException):
            self.sess.pool.get_connection()

        # set port back
        self.sess.pool.account.port = saved_port

    def test_1_multiple_disconnect(self):
        with self.sess.pool.get_connection() as conn:
            # disconnect() may now be called multiple times without error.
            # (Note, here it is called implicitly upon exiting the with-block.)
            conn.disconnect()

    def test_2_multiple_disconnect(self):
        conn = self.sess.pool.get_connection()
        # disconnect() may now be called multiple times without error.
        conn.disconnect()
        conn.disconnect()

    def test_reply_failure(self):
        with self.sess.pool.get_connection() as conn:
            # close connection
            conn.disconnect()

            # try sending reply
            with self.assertRaises(NetworkException):
                conn.reply(0)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
