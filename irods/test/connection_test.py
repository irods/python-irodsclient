#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import tempfile
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
        # Make sure no connections are cached in self.sess.pool.idle to be grabbed by get_connection().
        # (Necessary after #418 fix; make_session() can probe server_version, which then leaves an idle conn.)
        self.sess.cleanup()
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

    def test_that_connection_timeout_works__issue_377(self):
        sess = self.sess
        h = helpers.home_collection(sess)
        logical_path = h + '/issue_377_test.file_timeout_test_on_chksum'
        rand = os.urandom(1024)*64
        obj = local_file = None
        try:
            # Create a large file.
            size = 1024**2 * 100
            with tempfile.NamedTemporaryFile(delete = False) as local_file:
                while local_file.tell() < size:
                    local_file.write(rand)
            obj = sess.data_objects.put(local_file.name, logical_path, return_data_object = True)

            # Set a very short socket timeout and remove all pre-existing socket connections.
            # This forces a new connection to be made for any ensuing connections to the iRODS server.

            sess = obj.manager.sess # Because of client-redirect it is possible that self.sess and
                                    # obj.manager.sess do not refer to the same object. In any case,
                                    # it is the latter of the two iRODSSession objects that is
                                    # involved in the data PUT connection.
            sess.connection_timeout = timeout = 0.01
            sess.cleanup()

            # Make sure the newly formed connection pool inherits the timeout value.
            self.assertAlmostEqual(sess.pool.connection_timeout, timeout)

            # Perform a time-consuming operation in the server (ie. computing the checksum of a
            # large data object) during which the socket will time out.
            with self.assertRaises(NetworkException):
                obj.chksum()
        finally:
            # Set the connection pool's socket timeout interval back to default, and clean up.
            sess.connection_timeout = None
            sess.cleanup()
            obj.unlink(force = True)
            if local_file:
                os.unlink(local_file.name)

    def assert_timeout_value_propagated_to_socket(self, session, timeout_value):
        session.collections.get(helpers.home_collection(session))
        conn = next(iter(session.pool.idle))
        self.assertEqual(conn.socket.gettimeout(), timeout_value)

    def test_connection_timeout_parameter_in_session_init__issue_377(self):
        timeout = 1.0
        sess = helpers.make_session(connection_timeout = timeout)
        self.assert_timeout_value_propagated_to_socket(sess, timeout)

    def test_assigning_session_connection_timeout__issue_377(self):
        sess = self.sess
        for timeout in (999999, None):
            sess.connection_timeout = timeout
            sess.cleanup()
            self.assert_timeout_value_propagated_to_socket(sess, timeout)

if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
