#! /usr/bin/env python
import unittest
import os
import sys

from irods.session import iRODSSession
from irods.exception import UserDoesNotExist
import config




class TestAdmin(unittest.TestCase):
    '''Suite of tests on admin operations
    '''
    
    # test data
    new_user_name = 'bobby'
    new_user_type = 'rodsuser'
    new_user_zone = config.IRODS_SERVER_ZONE    # use remote zone when creation is supported
    
    

    def setUp(self):
        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)
        

        
    def tearDown(self):
        '''Close connections
        '''
        self.sess.cleanup()

    def test_create_and_delete_local_user(self):
        """
        """
        # user should not be already present
        self.assertRaises(UserDoesNotExist, lambda: self.sess.users.get(self.new_user_name))
        
        # create user
        self.sess.users.create(self.new_user_name, self.new_user_type)
        
        # retrieve user
        user = self.sess.users.get(self.new_user_name)
        repr(user)  # for coverage
        
        # assertions
        self.assertEqual(user.name, self.new_user_name)
        self.assertEqual(user.zone, config.IRODS_SERVER_ZONE)
        
        # delete user
        self.sess.users.remove(self.new_user_name)

        # user should be gone
        self.assertRaises(UserDoesNotExist, lambda: self.sess.users.get(self.new_user_name))


    def test_create_and_delete_user_with_zone(self):
        """
        """
        # user should not be already present
        self.assertRaises(UserDoesNotExist, lambda: self.sess.users.get(self.new_user_name, self.new_user_zone))
        
        # create user
        self.sess.users.create(self.new_user_name, self.new_user_type, self.new_user_zone)
        
        # retrieve user
        user = self.sess.users.get(self.new_user_name, self.new_user_zone)
        
        # assertions
        self.assertEqual(user.name, self.new_user_name)
        self.assertEqual(user.zone, self.new_user_zone)
        
        # delete user
        self.sess.users.remove(self.new_user_name, self.new_user_zone)

        # user should be gone
        self.assertRaises(UserDoesNotExist, lambda: self.sess.users.get(self.new_user_name, self.new_user_zone))


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
