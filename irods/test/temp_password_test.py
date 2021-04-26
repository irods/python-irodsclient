#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import unittest
from irods.exception import UserDoesNotExist
from irods.session import iRODSSession
import irods.test.helpers as helpers


class TestTempPassword(unittest.TestCase):
    """ Suite of tests for setting and getting temporary passwords as rodsadmin or rodsuser
    """
    admin = None
    new_user = 'bobby'
    password = 'foobar'

    @classmethod
    def setUpClass(cls):
        cls.admin = helpers.make_session()

    @classmethod
    def tearDownClass(cls):
        cls.admin.cleanup()

    def test_temp_password(self):
        # Make a new user
        self.admin.users.create(self.new_user, 'rodsuser')
        self.admin.users.modify(self.new_user, 'password', self.password)

        # Login as the new test user, to retrieve a temporary password
        with iRODSSession(host=self.admin.host,
                          port=self.admin.port,
                          user=self.new_user,
                          password=self.password,
                          zone=self.admin.zone) as session:
            # Obtain the temporary password
            conn = session.pool.get_connection()
            temp_password = conn.temp_password()

        # Open a new session with the temporary password
        with iRODSSession(host=self.admin.host,
                          port=self.admin.port,
                          user=self.new_user,
                          password=temp_password,
                          zone=self.admin.zone) as session:

            # do something that connects to the server
            session.users.get(self.admin.username)

        # delete new user
        self.admin.users.remove(self.new_user)

        # user should be gone
        with self.assertRaises(UserDoesNotExist):
            self.admin.users.get(self.new_user)

    def test_set_temp_password(self):
        # make a new user
        temp_user = self.admin.users.create(self.new_user, 'rodsuser')

        # obtain a temporary password as rodsadmin for another user
        temp_password = temp_user.temp_password()

        # open a session as the new user
        with iRODSSession(host=self.admin.host,
                          port=self.admin.port,
                          user=self.new_user,
                          password=temp_password,
                          zone=self.admin.zone) as session:

            # do something that connects to the server
            session.users.get(self.new_user)

        # delete new user
        self.admin.users.remove(self.new_user)

        # user should be gone
        with self.assertRaises(UserDoesNotExist):
            self.admin.users.get(self.new_user)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
