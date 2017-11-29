#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import unittest
from irods.exception import UserGroupDoesNotExist
import irods.test.helpers as helpers
from six.moves import range


class TestUserGroup(unittest.TestCase):

    def setUp(self):
        self.sess = helpers.make_session()

    def tearDown(self):
        '''Close connections
        '''
        self.sess.cleanup()

    def test_create_group(self):
        group_name = "test_group"

        # group should not be already present
        with self.assertRaises(UserGroupDoesNotExist):
            self.sess.user_groups.get(group_name)

        # create group
        group = self.sess.user_groups.create(group_name)

        # assertions
        self.assertEqual(group.name, group_name)
        self.assertEqual(
            repr(group), "<iRODSUserGroup {0} {1}>".format(group.id, group_name))

        # delete group
        group.remove()

        # group should be gone
        with self.assertRaises(UserGroupDoesNotExist):
            self.sess.user_groups.get(group_name)

    def test_add_users_to_group(self):
        group_name = "test_group"
        group_size = 15
        base_user_name = "test_user"

        # group should not be already present
        with self.assertRaises(UserGroupDoesNotExist):
            self.sess.user_groups.get(group_name)

        # create test group
        group = self.sess.user_groups.create(group_name)

        # create test users names
        test_user_names = []
        for i in range(group_size):
            test_user_names.append(base_user_name + str(i))

        # make test users and add them to test group
        for test_user_name in test_user_names:
            user = self.sess.users.create(test_user_name, 'rodsuser')
            group.addmember(user.name)

        # list group members
        member_names = [user.name for user in group.members]

        # compare lists
        self.assertSetEqual(set(member_names), set(test_user_names))

        # exercise iRODSUserGroup.hasmember()
        for test_user_name in test_user_names:
            self.assertTrue(group.hasmember(test_user_name))

        # remove test users from group and delete them
        for test_user_name in test_user_names:
            user = self.sess.users.get(test_user_name)
            group.removemember(user.name)
            user.remove()

        # delete group
        group.remove()

        # group should be gone
        with self.assertRaises(UserGroupDoesNotExist):
            self.sess.user_groups.get(group_name)


    def test_user_dn(self):
        # https://github.com/irods/irods/issues/3620
        if self.sess.server_version == (4, 2, 1):
            self.skipTest('Broken in 4.2.1')

        user_name = "testuser"
        user_DNs = ['foo', 'bar']

        # create user
        user = self.sess.users.create(user_name, 'rodsuser')

        # expect no dn
        self.assertEqual(user.dn, [])

        # add dn
        user.modify('addAuth', user_DNs[0])
        self.assertEqual(user.dn[0], user_DNs[0])

        # add other dn
        user.modify('addAuth', user_DNs[1])
        self.assertEqual(user.dn, user_DNs)

        # remove first dn
        user.modify('rmAuth', user_DNs[0])

        # confirm removal
        self.assertEqual(user.dn, user_DNs[1:])

        # delete user
        user.remove()


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
