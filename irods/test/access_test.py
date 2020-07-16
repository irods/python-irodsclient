#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import unittest
from irods.access import iRODSAccess
from irods.user import iRODSUser
from irods.models import User
import irods.test.helpers as helpers
from irods.column import In


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

    mapping = dict( [ (i,i) for i in ('modify object', 'read object', 'own') ] +
                    [ ('write','modify object') , ('read', 'read object') ]
                  )

    @classmethod
    def perms_lists_symm_diff ( cls, a_iter, b_iter ):
        fields = lambda perm: (cls.mapping[perm.access_name], perm.user_name, perm.user_zone)
        A = set (map(fields,a_iter))
        B = set (map(fields,b_iter))
        return (A-B) | (B-A)

    def test_raw_acls__207(self):
        data = helpers.make_object(self.sess,"/".join((self.coll_path,"test_obj")))
        eg = eu = fg = fu = None
        try:
            eg = self.sess.user_groups.create ('egrp')
            eu = self.sess.users.create ('edith','rodsuser')
            eg.addmember(eu.name,eu.zone)
            fg = self.sess.user_groups.create ('fgrp')
            fu = self.sess.users.create ('frank','rodsuser')
            fg.addmember(fu.name,fu.zone)
            my_ownership = set([('own', self.sess.username, self.sess.zone)])
            #--collection--
            perms1data = [ iRODSAccess ('write',self.coll_path, eg.name, self.sess.zone),
                           iRODSAccess ('read', self.coll_path, fu.name, self.sess.zone)
                         ]
            for perm in perms1data: self.sess.permissions.set ( perm )
            p1 = self.sess.permissions.get ( self.coll, report_raw_acls = True)
            self.assertEqual(self.perms_lists_symm_diff( perms1data, p1 ), my_ownership)
            #--data object--
            perms2data = [ iRODSAccess ('write',data.path, fg.name, self.sess.zone),
                           iRODSAccess ('read', data.path, eu.name, self.sess.zone)
                         ]
            for perm in perms2data: self.sess.permissions.set ( perm )
            p2 = self.sess.permissions.get ( data, report_raw_acls = True)
            self.assertEqual(self.perms_lists_symm_diff( perms2data, p2 ), my_ownership)
        finally:
            ids_for_delete = [ u.id for u in (fu,fg,eu,eg) if u is not None ]
            for u in [ iRODSUser(self.sess.users,row)
                       for row in self.sess.query(User).filter(In(User.id, ids_for_delete)) ]:
                u.remove()


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
