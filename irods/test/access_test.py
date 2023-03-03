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
        VERSION_DEPENDENT_STRINGS = { 'MODIFY':'modify_object', 'READ':'read_object' } if self.sess.server_version >= (4,3) \
                               else { 'MODIFY':'modify object', 'READ':'read object' }
        self.mapping = dict( [(i,i) for i in ( 'own', VERSION_DEPENDENT_STRINGS['MODIFY'], VERSION_DEPENDENT_STRINGS['READ'])] +
                             [('write',VERSION_DEPENDENT_STRINGS['MODIFY']), ('read', VERSION_DEPENDENT_STRINGS['READ'])] )

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
            self.sess.acls.get(filename)

        # get object's ACLs
        # only one for now, the owner's own access
        acl = self.sess.acls.get(obj)[0]

        # check values
        self.assertEqual(acl.access_name, 'own')
        self.assertEqual(acl.user_zone, user.zone)
        self.assertEqual(acl.user_name, user.name)

        # check repr()
        self.assertEqual(
            repr(acl), "<iRODSAccess own {path} {name}({type}) {zone}>".format(path=path, **vars(user)))

        # remove object
        self.sess.data_objects.unlink(path)


    def test_set_inherit_acl(self):

        acl1 = iRODSAccess('inherit', self.coll_path)
        self.sess.acls.set(acl1)
        c = self.sess.collections.get(self.coll_path)
        self.assertTrue(c.inheritance)

        acl2 = iRODSAccess('noinherit', self.coll_path)
        self.sess.acls.set(acl2)
        c = self.sess.collections.get(self.coll_path)
        self.assertFalse(c.inheritance)

    def test_available_permissions__420_422(self):
        # Cycle through access levels (strings available via session.available_permissions) and test, with
        # a string compare, that the "set" access level matches the "get" access level.
        user = data = None
        try:
            user = self.sess.users.create('bob','rodsuser')
            data = self.sess.data_objects.create('{}/obj_422'.format(helpers.home_collection(self.sess)))
            permission_strings = self.sess.available_permissions.keys()
            for perm in permission_strings:
                access = iRODSAccess(perm, data.path, 'bob')
                self.sess.acls.set( access )
                a = [acl for acl in self.sess.acls.get( data ) if acl.user_name == 'bob']
                if perm == 'null':
                    self.assertEqual(len(a),0)
                else:
                    self.assertEqual(len(a),1)
                    self.assertEqual(access.access_name,a[0].access_name)
        finally:
            if user: user.remove()
            if data: data.unlink(force=True)

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

            self.sess.acls.set(acl_read)
            self.sess.acls.set(acl_inherit)

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
                self.sess.acls.set( acl1, recursive = recursionTruth )
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
        self.sess.acls.set(acl1)

        # get object's ACLs
        acl = self.sess.acls.get(obj)[0]  # owner's write access

        # check values
        self.assertEqual(acl.access_name, self.mapping['write'])
        self.assertEqual(acl.user_zone, user.zone)
        self.assertEqual(acl.user_name, user.name)

        # reset permission to own
        acl1 = iRODSAccess('own', path, user.name, user.zone)
        self.sess.acls.set(acl1)

        # remove object
        self.sess.data_objects.unlink(path)

    def test_set_collection_acl(self):
        # use test coll
        coll = self.coll

        # get current user info
        user = self.sess.users.get(self.sess.username, self.sess.zone)

        # set permission to write
        acl1 = iRODSAccess('write', coll.path, user.name, user.zone)
        self.sess.acls.set(acl1)

        # get collection's ACLs
        acl = self.sess.acls.get(coll)[0]  # owner's write access

        # check values
        self.assertEqual(acl.access_name, self.mapping['write'])
        self.assertEqual(acl.user_zone, user.zone)
        self.assertEqual(acl.user_name, user.name)

        # reset permission to own
        acl1 = iRODSAccess('own', coll.path, user.name, user.zone)
        self.sess.acls.set(acl1)

    def perms_lists_symm_diff ( self, a_iter, b_iter ):
        fields = lambda perm: (self.mapping[perm.access_name], perm.user_name, perm.user_zone)
        A = set (map(fields,a_iter))
        B = set (map(fields,b_iter))
        return (A-B) | (B-A)

    def test_raw_acls__207(self):
        data = helpers.make_object(self.sess,"/".join((self.coll_path,"test_obj")))
        eg = eu = fg = fu = None
        try:
            eg = self.sess.groups.create ('egrp')
            eu = self.sess.users.create ('edith','rodsuser')
            eg.addmember(eu.name,eu.zone)
            fg = self.sess.groups.create ('fgrp')
            fu = self.sess.users.create ('frank','rodsuser')
            fg.addmember(fu.name,fu.zone)
            my_ownership = set([('own', self.sess.username, self.sess.zone)])
            #--collection--
            perms1data = [ iRODSAccess ('write',self.coll_path, eg.name, self.sess.zone),
                           iRODSAccess ('read', self.coll_path, fu.name, self.sess.zone)
                         ]
            for perm in perms1data: self.sess.acls.set ( perm )
            p1 = self.sess.permissions.get ( self.coll, report_raw_acls = True)
            self.assertEqual(self.perms_lists_symm_diff( perms1data, p1 ), my_ownership)
            #--data object--
            perms2data = [ iRODSAccess ('write',data.path, fg.name, self.sess.zone),
                           iRODSAccess ('read', data.path, eu.name, self.sess.zone)
                         ]
            for perm in perms2data: self.sess.acls.set ( perm )
            p2 = self.sess.permissions.get ( data, report_raw_acls = True)
            self.assertEqual(self.perms_lists_symm_diff( perms2data, p2 ), my_ownership)
        finally:
            ids_for_delete = [ u.id for u in (fu,fg,eu,eg) if u is not None ]
            for u in [ iRODSUser(self.sess.users,row)
                       for row in self.sess.query(User).filter(In(User.id, ids_for_delete)) ]:
                u.remove()

    def test_ses_acls_data_and_collection_395_396(self):
        ses = self.sess
        try:
            # Create rodsusers alice and bob, and make bob a member of the 'team' group.

            self.alice = ses.users.create('alice','rodsuser')
            self.bob = ses.users.create('bob','rodsuser')
            self.team = ses.groups.create('team')
            self.team.addmember('bob')
            ses.users.modify('bob', 'password', 'bpass')

            # Create a collection and a data object.

            home = helpers.home_collection(ses)
            self.coll_395 = ses.collections.create(home + "/coll-395")
            self.data = ses.data_objects.create(self.coll_395.path +"/data")
            with self.data.open('w') as f: f.write(b'contents-395')

            # Make assertions for both filesystem object types (collection and data):

            for obj in self.coll_395, self.data:

                # Add ACLs
                for access in iRODSAccess('read',obj.path,'team'),  iRODSAccess('write',obj.path,'alice'):
                    ses.acls.set(access)

                ACLs = ses.acls.get(obj)

                # Assert that we can detect alice's write permissions.
                self.assertEqual(1, len([ac for ac in ACLs if (ac.access_name,ac.user_name)
                                                         == (self.mapping['write'],'alice')]))

                # Test that the 'team' ACL is listed as a rodsgroup ...

                team_acl = [ac for ac in ACLs if ac.user_name == 'team']
                self.assertEqual(1, len(team_acl))
                self.assertEqual(team_acl[0].user_type,
                                 'rodsgroup')

                # ... and also that 'bob' (a 'team' member) is not listed explicitly.
                self.assertEqual(0, len([ac for ac in ACLs if ac.user_name == 'bob']))

            # verify that bob can access the data object as a member of team.
            with iRODSSession( host=ses.host,
                               user='bob',
                               port=ses.port,
                               zone=ses.zone,
                               password = 'bpass') as bob:
                self.assertTrue( bob.data_objects.open(self.data.path,'r').read(), b'contents-395' )

        finally:
            self.coll_395.remove(recurse = True,force = True)
            self.bob.remove()
            self.alice.remove()
            self.team.remove()


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
