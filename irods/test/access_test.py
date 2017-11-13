#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import unittest
from irods.access import iRODSAccess
import irods.test.helpers as helpers


class TestAccess(unittest.TestCase):

    def setUp(self):
        self.sess = helpers.make_session()

        # Create test collection
        self.coll_path = '/{}/home/{}/test_dir'.format(self.sess.zone, self.sess.username)
        self.coll = helpers.make_collection(self.sess, self.coll_path)

    def tearDown(self):
        '''Remove test data and close connections
        '''
        self.coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def test_list_acl(self):
        # test args
        collection = self.coll_path
        filename = 'foo'

        # get current user info
        user = self.sess.users.get(self.sess.username, self.sess.zone)

        # make object in test collection
        path = "{collection}/{filename}".format(**locals())
        obj = helpers.make_object(self.sess, path)

        # get object
        obj = self.sess.data_objects.get(path)

        # test exception
        with self.assertRaises(TypeError):
            self.sess.permissions.get(filename)

        # get object's ACLs
        # only one for now, the owner's own access
        acl = self.sess.permissions.get(obj)[0]

        # check values
        self.assertEqual(acl.access_name, 'own')
        self.assertEqual(acl.user_zone, user.zone)
        self.assertEqual(acl.user_name, user.name)

        # check repr()
        self.assertEqual(
            repr(acl), "<iRODSAccess own {path} {name} {zone}>".format(path=path, **vars(user)))

        # remove object
        self.sess.data_objects.unlink(path)

    def test_set_data_acl(self):
        # test args
        collection = self.coll_path
        filename = 'foo'

        # get current user info
        user = self.sess.users.get(self.sess.username, self.sess.zone)

        # make object in test collection
        path = "{collection}/{filename}".format(**locals())
        obj = helpers.make_object(self.sess, path)

        # get object
        obj = self.sess.data_objects.get(path)

        # set permission to write
        acl1 = iRODSAccess('write', path, user.name, user.zone)
        self.sess.permissions.set(acl1)

        # get object's ACLs
        acl = self.sess.permissions.get(obj)[0]  # owner's write access

        # check values
        self.assertEqual(acl.access_name, 'modify object')
        self.assertEqual(acl.user_zone, user.zone)
        self.assertEqual(acl.user_name, user.name)

        # reset permission to own
        acl1 = iRODSAccess('own', path, user.name, user.zone)
        self.sess.permissions.set(acl1)

        # remove object
        self.sess.data_objects.unlink(path)

    def test_set_collection_acl(self):
        # use test coll
        coll = self.coll

        # get current user info
        user = self.sess.users.get(self.sess.username, self.sess.zone)

        # set permission to write
        acl1 = iRODSAccess('write', coll.path, user.name, user.zone)
        self.sess.permissions.set(acl1)

        # get collection's ACLs
        acl = self.sess.permissions.get(coll)[0]  # owner's write access

        # check values
        self.assertEqual(acl.access_name, 'modify object')
        self.assertEqual(acl.user_zone, user.zone)
        self.assertEqual(acl.user_name, user.name)

        # reset permission to own
        acl1 = iRODSAccess('own', coll.path, user.name, user.zone)
        self.sess.permissions.set(acl1)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
