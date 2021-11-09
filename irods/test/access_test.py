#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import unittest
from irods.access import iRODSAccess
from irods.user import iRODSUser
from irods.session import iRODSSession
from irods.models import User,Collection,DataObject
from irods.collection import iRODSCollection
import irods.test.helpers as helpers
from irods.column import In, Like


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


    def test_set_inherit_acl(self):

        acl1 = iRODSAccess('inherit', self.coll_path)
        self.sess.permissions.set(acl1)
        c = self.sess.collections.get(self.coll_path)
        self.assertTrue(c.inheritance)

        acl2 = iRODSAccess('noinherit', self.coll_path)
        self.sess.permissions.set(acl2)
        c = self.sess.collections.get(self.coll_path)
        self.assertFalse(c.inheritance)

    def test_set_inherit_and_test_sub_objects (self):
        DEPTH = 3
        OBJ_PER_LVL = 1
        deepcoll = user = None
        test_coll_path = self.coll_path + "/test"
        try:
            deepcoll = helpers.make_deep_collection(self.sess, test_coll_path, object_content = 'arbitrary',
                                                    depth=DEPTH, objects_per_level=OBJ_PER_LVL)
            user = self.sess.users.create('bob','rodsuser')
            user.modify ('password','bpass')

            acl_inherit = iRODSAccess('inherit', deepcoll.path)
            acl_read = iRODSAccess('read', deepcoll.path, 'bob')

            self.sess.permissions.set(acl_read)
            self.sess.permissions.set(acl_inherit)

            # create one new object and one new collection *after* ACL's are applied
            new_object_path = test_coll_path + "/my_data_obj"
            with self.sess.data_objects.open( new_object_path ,'w') as f: f.write(b'some_content')

            new_collection_path = test_coll_path + "/my_colln_obj"
            new_collection = self.sess.collections.create( new_collection_path )

            coll_IDs = [c[Collection.id] for c in
                            self.sess.query(Collection.id).filter(Like(Collection.name , deepcoll.path + "%"))]

            D_rods = list(self.sess.query(Collection.name,DataObject.name).filter(
                                                                          In(DataObject.collection_id, coll_IDs )))

            self.assertEqual (len(D_rods), OBJ_PER_LVL*DEPTH+1) # counts the 'older' objects plus one new object

            with iRODSSession (port=self.sess.port, zone=self.sess.zone, host=self.sess.host,
                               user='bob', password='bpass') as bob:

                D = list(bob.query(Collection.name,DataObject.name).filter(
                                                                    In(DataObject.collection_id, coll_IDs )))

                # - bob should only see the new data object, but none existing before ACLs were applied

                self.assertEqual( len(D), 1 )
                D_names = [_[Collection.name] + "/" + _[DataObject.name] for _ in D]
                self.assertEqual( D[0][DataObject.name], 'my_data_obj' )

                # - bob should be able to read the new data object

                with bob.data_objects.get(D_names[0]).open('r') as f:
                    self.assertGreater( len(f.read()), 0)

                C = list(bob.query(Collection).filter( In(Collection.id, coll_IDs )))
                self.assertEqual( len(C), 2 ) # query should return only the top-level and newly created collections
                self.assertEqual( sorted([c[Collection.name] for c in C]),
                                  sorted([new_collection.path, deepcoll.path]) )
        finally:
            if user: user.remove()
            if deepcoll: deepcoll.remove(force = True, recurse = True)

    def test_set_inherit_acl_depth_test(self):
        DEPTH = 3  # But test is valid for any DEPTH > 1
        for recursionTruth in (True, False):
            deepcoll = None
            try:
                test_coll_path = self.coll_path + "/test"
                deepcoll = helpers.make_deep_collection(self.sess, test_coll_path, depth=DEPTH, objects_per_level=2)
                acl1 = iRODSAccess('inherit', deepcoll.path)
                self.sess.permissions.set( acl1, recursive = recursionTruth )
                test_subcolls = set( iRODSCollection(self.sess.collections,_)
                                for _ in self.sess.query(Collection).filter(Like(Collection.name, deepcoll.path + "/%")) )

                # assert top level collection affected
                test_coll = self.sess.collections.get(test_coll_path)
                self.assertTrue( test_coll.inheritance )
                #
                # assert lower level collections affected only for case when recursive = True
                subcoll_truths = [ (_.inheritance == recursionTruth) for _ in test_subcolls ]
                self.assertEqual( len(subcoll_truths), DEPTH-1 )
                self.assertTrue( all(subcoll_truths) )
            finally:
                if deepcoll: deepcoll.remove(force = True, recurse = True)


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
