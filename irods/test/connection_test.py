#! /usr/bin/env python

import io
import logging
import numbers
import os
import re
import sys
import tempfile
import unittest
from irods import MAXIMUM_CONNECTION_TIMEOUT
from irods.exception import NetworkException, CAT_INVALID_AUTHENTICATION
import irods.session
import irods.test.helpers as helpers
from irods.test.helpers import server_side_sleep
from irods.helpers import temporarily_assign_attribute as temp_setter


class TestConnections(unittest.TestCase):

    def setUp(self):
        self.sess = helpers.make_session()

    def tearDown(self):
        """Close connections"""
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

    def test_server_version_without_authentication__issue_688(self):
        sess = self.sess

        # Make a session object that cannot authenticate.
        non_authenticating_session = irods.session.iRODSSession(
            host=sess.host,
            port=sess.port,
            user=sess.username,
            zone=sess.zone,
            # No password.
        )

        # Test server_version_without_auth method returns a value.
        version_tup = non_authenticating_session.server_version_without_auth()

        # Test returned value is non-empty "version" tuple, i.e. holds only integer values.
        self.assertGreater(len(version_tup), 0)
        self.assertFalse(any(not isinstance(_, numbers.Integral) for _ in version_tup))

        # Test that the older server_version property fails for the unauthenticated session object.
        with self.assertRaises(CAT_INVALID_AUTHENTICATION):
            _ = non_authenticating_session.server_version

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
        logical_path = h + "/issue_377_test.file_timeout_test_on_chksum"
        rand = os.urandom(1024) * 64
        obj = local_file = None
        try:
            # Create a large file.
            size = 1024**2 * 100
            with tempfile.NamedTemporaryFile(delete=False) as local_file:
                while local_file.tell() < size:
                    local_file.write(rand)
            obj = sess.data_objects.put(
                local_file.name, logical_path, return_data_object=True
            )

            # Set a very short socket timeout and remove all pre-existing socket connections.
            # This forces a new connection to be made for any ensuing connections to the iRODS server.

            sess = (
                obj.manager.sess
            )  # Because of client-redirect it is possible that self.sess and
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
            obj.unlink(force=True)
            if local_file:
                os.unlink(local_file.name)

    def _assert_timeout_value_is_propagated_to_all_sockets__issue_569(
        self, session, expected_timeout_value="POOL_TIMEOUT_SETTING"
    ):
        pool = session.pool
        new_conn = None
        if expected_timeout_value == "POOL_TIMEOUT_SETTING":
            expected_timeout_value = pool.connection_timeout
        connections = set()
        # make sure idle pool is not empty
        session.collections.get(helpers.home_collection(session))
        # On any connections thus far created, check that their internal socket objects are set to the expected timeout value.
        try:
            # Peel connections off the idle pool and check each for the expected timeout value, but don't release them to that pool yet.
            while pool.idle:
                # Peel a connection (guaranteed newly-allocated for purposes of this test) and check for the proper timeout.
                conn = pool.get_connection()
                connections |= {conn}
                self.assertEqual(conn.socket.gettimeout(), expected_timeout_value)

            # Get an additional connection while idle pool is empty; this way, we know it to be newly-allocated.
            new_conn = pool.get_connection()

            # Check the expected timeout applies to the newly-allocated connection
            self.assertEqual(new_conn.socket.gettimeout(), expected_timeout_value)

        finally:
            # Release and destroy the connection that was newly-allocated for this test.
            if new_conn:
                new_conn.release(destroy=True)
            # Release connections that had been cached, by the same normal mechanism the API endpoints indirectly employ.
            for conn in connections:
                pool.release_connection(conn)

    def test_connection_timeout_parameter_in_session_init__issue_377(self):
        timeout = 1.0
        sess = helpers.make_session(connection_timeout=timeout)
        self._assert_timeout_value_is_propagated_to_all_sockets__issue_569(
            sess, timeout
        )

    def test_assigning_session_connection_timeout__issue_377(self):
        sess = helpers.make_session()
        for timeout in (999999, None):
            sess.connection_timeout = timeout
            self._assert_timeout_value_is_propagated_to_all_sockets__issue_569(
                sess, timeout
            )

    def test_assigning_session_connection_timeout_to_invalid_values__issue_569(self):
        sess = helpers.make_session()
        DESIRED_TIMEOUT = 64.25
        sess.connection_timeout = DESIRED_TIMEOUT
        # Test our desired connection pool default timeout has taken hold.
        self.assertEqual(sess.connection_timeout, DESIRED_TIMEOUT)

        # Test that bad timeout values are met with an exception.
        for value in (float("NaN"), -float("Inf"), -1, 0, 0.0, "banana"):
            with self.assertRaises(ValueError):
                sess.connection_timeout = value

    def test_assigning_session_connection_timeout_to_large_values__issue_623(self):
        # Test use of a too-large timeout in iRODSSession constructor as well as on assignment to the
        # iRODSSession property 'connection_timeout'.  In both cases, error checking and hard-limiting
        # should be immediate.
        sess = helpers.make_session(connection_timeout=MAXIMUM_CONNECTION_TIMEOUT + 1)
        # The session attribute '_cached_connection_timeout' is where the session timeout value is kept
        # safe for whenever a Pool sub-object is initialized (or re-initialized).
        self.assertEqual(sess._cached_connection_timeout, MAXIMUM_CONNECTION_TIMEOUT)

        # Make (and check) a change of the connection_timeout value so that second of the surrounding
        # equality assertions does not accidentally succeed due to the value remaining untouched.
        sess.connection_timeout = 1
        self.assertEqual(sess._cached_connection_timeout, 1)

        sess.connection_timeout = MAXIMUM_CONNECTION_TIMEOUT + 1
        self.assertEqual(sess._cached_connection_timeout, MAXIMUM_CONNECTION_TIMEOUT)

        self.assertEqual(sess.pool.connection_timeout, MAXIMUM_CONNECTION_TIMEOUT)

    def test_assigning_session_connection_timeout__issue_569(self):
        sess = helpers.make_session()
        old_timeout = sess.connection_timeout

        with temp_setter(sess, "connection_timeout", 1.0):
            # verify we can reproduce a NetworkException from a server timeout
            with self.assertRaises(NetworkException):
                server_side_sleep(sess, 2.5)
            # temporarily suspend timeouts on a session
            with temp_setter(sess, "connection_timeout", None):
                server_side_sleep(sess, 2.5)
            # temporarily increase (from 1.0 to 4) the timeout on a session
            with temp_setter(sess, "connection_timeout", 4):
                server_side_sleep(sess, 2.5)
        self.assertEqual(old_timeout, sess.connection_timeout)
        self._assert_timeout_value_is_propagated_to_all_sockets__issue_569(
            sess, old_timeout
        )

    def test_legacy_auth_used_with_force_legacy_auth_configuration__issue_499(self):
        import irods.client_configuration as config

        with config.loadlines(
            entries=[dict(setting="legacy_auth.force_legacy_auth", value=True)]
        ):
            stream = io.StringIO()
            logger = logging.getLogger("irods.connection")
            with helpers.enableLogging(
                logger, logging.StreamHandler, (stream,), level_=logging.INFO
            ):
                with temp_setter(logger, "propagate", False):
                    helpers.make_session().collections.get("/")
        regex = re.compile("^.*Native auth.*(in legacy auth).*$", re.MULTILINE)
        self.assertTrue(regex.search(stream.getvalue()))


if __name__ == "__main__":
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath("../.."))
    unittest.main()
