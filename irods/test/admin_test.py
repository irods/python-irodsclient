#! /usr/bin/env python
import os
import sys
import socket

if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest

from irods.models import User
from irods.session import iRODSSession
from irods.exception import UserDoesNotExist
import irods.test.config as config


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

    def test_create_delete_local_user(self):
        # user should not be already present
        self.assertRaises(
            UserDoesNotExist, lambda: self.sess.users.get(self.new_user_name))

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
        self.assertRaises(
            UserDoesNotExist, lambda: self.sess.users.get(self.new_user_name))

    def test_create_delete_user_zone(self):
        # user should not be already present
        self.assertRaises(UserDoesNotExist, lambda: self.sess.users.get(
            self.new_user_name, self.new_user_zone))

        # create user
        self.sess.users.create(
            self.new_user_name, self.new_user_type, self.new_user_zone)

        # retrieve user
        user = self.sess.users.get(self.new_user_name, self.new_user_zone)

        # assertions
        self.assertEqual(user.name, self.new_user_name)
        self.assertEqual(user.zone, self.new_user_zone)

        # delete user
        self.sess.users.remove(self.new_user_name, self.new_user_zone)

        # user should be gone
        self.assertRaises(UserDoesNotExist, lambda: self.sess.users.get(
            self.new_user_name, self.new_user_zone))

    def test_modify_user_type(self):
        # make new regular user
        self.sess.users.create(self.new_user_name, self.new_user_type)

        # check type
        row = self.sess.query(User.type).filter(
            User.name == self.new_user_name).one()
        self.assertEqual(row[User.type], self.new_user_type)

        # change type to rodsadmin
        self.sess.users.modify(self.new_user_name, 'type', 'rodsadmin')

        # check type again
        row = self.sess.query(User.type).filter(
            User.name == self.new_user_name).one()
        self.assertEqual(row[User.type], 'rodsadmin')

        # delete user
        self.sess.users.remove(self.new_user_name)

        # user should be gone
        self.assertRaises(
            UserDoesNotExist, lambda: self.sess.users.get(self.new_user_name))

    def test_make_new_ufs_resource(self):
        # test data
        resc_name = 'temporary_test_resource'
        if  config.IRODS_SERVER_VERSION < (4, 0, 0):
            resc_type = 'unix file system'
            resc_class = 'cache'
        else:
            resc_type = 'unixfilesystem'
            resc_class = ''
        resc_host = config.IRODS_SERVER_HOST
        resc_path = '/tmp/' + resc_name
        dummy_str = 'blah'

        coll_path = '/{0}/home/{1}/test_dir'.format(
            config.IRODS_SERVER_ZONE, config.IRODS_USER_USERNAME)
        obj_name = 'test1'
        obj_path = '{0}/{1}'.format(coll_path, obj_name)

        # make new resource
        self.sess.resources.create(resc_name, resc_type, resc_host, resc_path, resource_class = resc_class)

        # retrieve resource
        resource = self.sess.resources.get(resc_name)
        repr(resource)  # for coverage

        # assertions
        self.assertEqual(resource.name, resc_name)

        # make test collection
        coll = self.sess.collections.create(coll_path)

        # create file on new resource
        obj = self.sess.data_objects.create(obj_path, resc_name)

        # write something to the file
        with obj.open('w+') as obj_desc:
            obj_desc.write(dummy_str)

        # refresh object (size has changed)
        obj = self.sess.data_objects.get(obj_path)

        # checks on file
        self.assertEqual(obj.name, obj_name)
        self.assertEqual(obj.size, len(dummy_str))

        # delete test collection
        coll.remove(recurse=True, force=True)

        # delete resource
        self.sess.resources.remove(resc_name)

    @unittest.skip('needs additional massaging in manager')
    def test_set_user_password(self):
        # make new regular user
        self.sess.users.create(self.new_user_name, self.new_user_type)

        # set password
        # self.sess.users.modify(self.new_user_name, 'password', 'blah')

        # try to open new session on behalf of user

        # delete user
        self.sess.users.remove(self.new_user_name)

        # user should be gone
        self.assertRaises(
            UserDoesNotExist, lambda: self.sess.users.get(self.new_user_name))


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
