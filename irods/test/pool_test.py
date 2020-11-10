#! /usr/bin/env python
from __future__ import absolute_import
import datetime
import os
import sys
import time
import unittest
import irods.test.helpers as helpers



class TestPool(unittest.TestCase):

    def setUp(self):
        self.sess = helpers.make_session(irods_env_file="./test-data/irods_environment.json")

    def tearDown(self):
        '''Close connections
        '''
        self.sess.cleanup()

    def test_release_connection(self):
        with self.sess.pool.get_connection():
            self.assertEqual(1, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))

        self.assertEqual(0, len(self.sess.pool.active))
        self.assertEqual(1, len(self.sess.pool.idle))

    def test_destroy_active(self):
        with self.sess.pool.get_connection() as conn:
            self.assertEqual(1, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))
            conn.release(destroy=True)

        self.assertEqual(0, len(self.sess.pool.active))
        self.assertEqual(0, len(self.sess.pool.idle))

    def test_destroy_idle(self):
        with self.sess.pool.get_connection():
            self.assertEqual(1, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))

        # cleanup all connections
        self.sess.cleanup()
        self.assertEqual(0, len(self.sess.pool.active))
        self.assertEqual(0, len(self.sess.pool.idle))

    def test_release_disconnected(self):
        with self.sess.pool.get_connection() as conn:
            self.assertEqual(1, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))
            conn.disconnect()

        # even though disconnected, gets put into idle
        self.assertEqual(0, len(self.sess.pool.active))
        self.assertEqual(1, len(self.sess.pool.idle))

        # should remove all connections
        self.sess.cleanup()
        self.assertEqual(0, len(self.sess.pool.active))
        self.assertEqual(0, len(self.sess.pool.idle))

    def test_connection_create_time(self):
        # Get a connection and record its object ID and create_time
        # Release the connection (goes from active to idle queue)
        # Again, get a connection. Should get the same connection back.
        # I.e., the object IDs should match. However, the new connection
        # should have a more recent 'last_used_time'
        conn_obj_id_1 = None
        conn_obj_id_2 = None
        create_time_1 = None
        create_time_2 = None
        last_used_time_1 = None
        last_used_time_2 = None

        with self.sess.pool.get_connection() as conn:
            conn_obj_id_1 = id(conn)
            curr_time = datetime.datetime.now()
            create_time_1 = conn.create_time
            last_used_time_1 = conn.last_used_time
            self.assertTrue(curr_time >= create_time_1)
            self.assertTrue(curr_time >= last_used_time_1)
            self.assertEqual(1, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))

            self.sess.pool.release_connection(conn)
            self.assertEqual(0, len(self.sess.pool.active))
            self.assertEqual(1, len(self.sess.pool.idle))

        with self.sess.pool.get_connection() as conn:
            conn_obj_id_2 = id(conn)
            curr_time = datetime.datetime.now()
            create_time_2 = conn.create_time
            last_used_time_2 = conn.last_used_time
            self.assertEqual(conn_obj_id_1, conn_obj_id_2)
            self.assertTrue(curr_time >= create_time_2)
            self.assertTrue(curr_time >= last_used_time_2)
            self.assertTrue(last_used_time_2 >= last_used_time_1)
            self.assertEqual(1, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))

            self.sess.pool.release_connection(conn)
            self.assertEqual(0, len(self.sess.pool.active))
            self.assertEqual(1, len(self.sess.pool.idle))

            self.sess.pool.release_connection(conn, True)
            self.assertEqual(0, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))

    def test_refresh_connection(self):
        # Set 'irods_connection_refresh_time' to '3' (in seconds) in
        # ~/.irods/irods_environment.json file. This means any connection
        # that was created more than 3 seconds ago will be dropped and
        # a new connection is created/returned. This is to avoid
        # issue with idle connections that are dropped.
        conn_obj_id_1 = None
        conn_obj_id_2 = None
        create_time_1 = None
        create_time_2 = None
        last_used_time_1 = None
        last_used_time_2 = None

        with self.sess.pool.get_connection() as conn:
            conn_obj_id_1 = id(conn)
            curr_time = datetime.datetime.now()
            create_time_1 = conn.create_time
            last_used_time_1 = conn.last_used_time
            self.assertTrue(curr_time >= create_time_1)
            self.assertTrue(curr_time >= last_used_time_1)
            self.assertEqual(1, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))

            self.sess.pool.release_connection(conn)
            self.assertEqual(0, len(self.sess.pool.active))
            self.assertEqual(1, len(self.sess.pool.idle))

        # Wait more than 'irods_connection_refresh_time' seconds,
        # which is set to 3. Connection object should have a different
        # object ID (as a new connection is created)
        time.sleep(5)

        with self.sess.pool.get_connection() as conn:
            conn_obj_id_2 = id(conn)
            curr_time = datetime.datetime.now()
            create_time_2 = conn.create_time
            last_used_time_2 = conn.last_used_time
            self.assertTrue(curr_time >= create_time_2)
            self.assertTrue(curr_time >= last_used_time_2)
            self.assertNotEqual(conn_obj_id_1, conn_obj_id_2)
            self.assertTrue(create_time_2 > create_time_1)
            self.assertEqual(1, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))

            self.sess.pool.release_connection(conn, True)
            self.assertEqual(0, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))

    def test_no_refresh_connection(self):
        # Set 'irods_connection_refresh_time' to '3' (in seconds) in
        # ~/.irods/irods_environment.json file. This means any connection
        # created more than 3 seconds ago will be dropped and
        # a new connection is created/returned. This is to avoid
        # issue with idle connections that are dropped.
        conn_obj_id_1 = None
        conn_obj_id_2 = None
        create_time_1 = None
        create_time_2 = None
        last_used_time_1 = None
        last_used_time_2 = None

        with self.sess.pool.get_connection() as conn:
            conn_obj_id_1 = id(conn)
            curr_time = datetime.datetime.now()
            create_time_1 = conn.create_time
            last_used_time_1 = conn.last_used_time
            self.assertTrue(curr_time >= create_time_1)
            self.assertTrue(curr_time >= last_used_time_1)
            self.assertEqual(1, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))

            self.sess.pool.release_connection(conn)
            self.assertEqual(0, len(self.sess.pool.active))
            self.assertEqual(1, len(self.sess.pool.idle))

        # Wait less than 'irods_connection_refresh_time' seconds,
        # which is set to 3. Connection object should have the same
        # object ID (as idle time is less than 'irods_connection_refresh_time')
        time.sleep(1)

        with self.sess.pool.get_connection() as conn:
            conn_obj_id_2 = id(conn)
            curr_time = datetime.datetime.now()
            create_time_2 = conn.create_time
            last_used_time_2 = conn.last_used_time
            self.assertTrue(curr_time >= create_time_2)
            self.assertTrue(curr_time >= last_used_time_2)
            self.assertEqual(conn_obj_id_1, conn_obj_id_2)
            self.assertTrue(create_time_2 >= create_time_1)
            self.assertEqual(1, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))

            self.sess.pool.release_connection(conn, True)
            self.assertEqual(0, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))

    def test_get_connection_refresh_time_no_env_file_input_param(self):
        connection_refresh_time = self.sess.get_connection_refresh_time(first_name="Magic", last_name="Johnson")
        self.assertEqual(connection_refresh_time, -1)

    def test_get_connection_refresh_time_none_existant_env_file(self):
        connection_refresh_time = self.sess.get_connection_refresh_time(irods_env_file="./test-data/irods_environment_non_existant.json")
        self.assertEqual(connection_refresh_time, -1)

    def test_get_connection_refresh_time_no_connection_refresh_field(self):
        connection_refresh_time = self.sess.get_connection_refresh_time(irods_env_file="./test-data/irods_environment_no_refresh_field.json")
        self.assertEqual(connection_refresh_time, -1)

    def test_get_connection_refresh_time_negative_connection_refresh_field(self):
        connection_refresh_time = self.sess.get_connection_refresh_time(irods_env_file="./test-data/irods_environment_negative_refresh_field.json")
        self.assertEqual(connection_refresh_time, -1)

    def test_get_connection_refresh_time(self):
        connection_refresh_time = self.sess.get_connection_refresh_time(irods_env_file="./test-data/irods_environment.json")
        self.assertEqual(connection_refresh_time, 3)

if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
