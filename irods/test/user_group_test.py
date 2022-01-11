#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import unittest
import tempfile
import shutil
from irods.exception import UserGroupDoesNotExist, UserDoesNotExist
from irods.meta import iRODSMetaCollection, iRODSMeta
from irods.models import User, UserGroup, UserMeta
from irods.session import iRODSSession
import irods.exception as ex
import irods.test.helpers as helpers
from six.moves import range


class TestUserGroup(unittest.TestCase):

    def setUp(self):
        self.sess = helpers.make_session()

    def tearDown(self):
        '''Close connections
        '''
        self.sess.cleanup()

    def test_modify_password__328(self):
        ses = self.sess
        if ses.users.get( ses.username ).type != 'rodsadmin':
            self.skipTest( 'Only a rodsadmin may run this test.')

        OLDPASS = 'apass'
        NEWPASS = 'newpass'
        try:
            ses.users.create('alice', 'rodsuser')
            ses.users.modify('alice', 'password', OLDPASS)

            with iRODSSession(user='alice', password=OLDPASS, host=ses.host, port=ses.port, zone=ses.zone) as alice:
                me = alice.users.get(alice.username)
                me.modify_password(OLDPASS, NEWPASS)

            with iRODSSession(user='alice', password=NEWPASS, host=ses.host, port=ses.port, zone=ses.zone) as alice:
                home = helpers.home_collection( alice )
                alice.collections.get( home ) # Non-trivial operation to test success!
        finally:
            try:
                ses.users.get('alice').remove()
            except UserDoesNotExist:
                pass

    @staticmethod
    def do_something(session):
        return session.username in [i[User.name] for i in session.query(User)]

    def test_modify_password_with_changing_auth_file__328(self):
        ses = self.sess
        if ses.users.get( ses.username ).type != 'rodsadmin':
            self.skipTest( 'Only a rodsadmin may run this test.')
        OLDPASS = 'apass'
        def generator(p = OLDPASS):
            n = 1
            old_pw = p
            while True:
                pw = p + str(n)
                yield old_pw, pw
                n += 1; old_pw = pw
        password_generator = generator()
        ENV_DIR = tempfile.mkdtemp()
        d = dict(password = OLDPASS, user = 'alice', host = ses.host, port = ses.port, zone = ses.zone)
        (alice_env, alice_auth) = helpers.make_environment_and_auth_files(ENV_DIR, **d)
        try:
            ses.users.create('alice', 'rodsuser')
            ses.users.modify('alice', 'password', OLDPASS)
            for modify_option, sess_factory in [ (alice_auth, lambda: iRODSSession(**d)),
                                                 (True,
                                                 lambda: helpers.make_session(irods_env_file = alice_env,
                                                                              irods_authentication_file = alice_auth)) ]:
                OLDPASS,NEWPASS=next(password_generator)
                with sess_factory() as alice_ses:
                    alice = alice_ses.users.get(alice_ses.username)
                    alice.modify_password(OLDPASS, NEWPASS, modify_irods_authentication_file = modify_option)
            d['password'] = NEWPASS
            with iRODSSession(**d) as session:
                self.do_something(session)           # can we still do stuff with the final value of the password?
        finally:
            shutil.rmtree(ENV_DIR)
            ses.users.remove('alice')

    def test_modify_password_with_incorrect_old_value__328(self):
        ses = self.sess
        if ses.users.get( ses.username ).type != 'rodsadmin':
            self.skipTest( 'Only a rodsadmin may run this test.')
        OLDPASS = 'apass'
        NEWPASS = 'newpass'
        ENV_DIR = tempfile.mkdtemp()
        try:
            ses.users.create('alice', 'rodsuser')
            ses.users.modify('alice', 'password', OLDPASS)
            d = dict(password = OLDPASS, user = 'alice', host = ses.host, port = ses.port, zone = ses.zone)
            (alice_env, alice_auth) = helpers.make_environment_and_auth_files(ENV_DIR, **d)
            session_factories = [
                       (lambda: iRODSSession(**d)),
                       (lambda: helpers.make_session( irods_env_file = alice_env, irods_authentication_file = alice_auth)),
            ]
            for factory in session_factories:
                with factory() as alice_ses:
                    alice = alice_ses.users.get(alice_ses.username)
                    with self.assertRaises( ex.CAT_PASSWORD_ENCODING_ERROR ):
                        alice.modify_password(OLDPASS + ".", NEWPASS)
            with iRODSSession(**d) as alice_ses:
                self.do_something(alice_ses)
        finally:
            shutil.rmtree(ENV_DIR)
            ses.users.remove('alice')

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
        self.assertEqual( sorted(user.dn), sorted(user_DNs) )

        # remove first dn
        user.modify('rmAuth', user_DNs[0])

        # confirm removal
        self.assertEqual(sorted(user.dn), sorted(user_DNs[1:]))

        # delete user
        user.remove()

    def test_group_metadata(self):
        group_name = "test_group"

        # group should not be already present
        with self.assertRaises(UserGroupDoesNotExist):
            self.sess.user_groups.get(group_name)

        group = None

        try:
            # create group
            group = self.sess.user_groups.create(group_name)

            # add metadata to group
            triple = ['key', 'value', 'unit']
            group.metadata[triple[0]] = iRODSMeta(*triple)

            result =  self.sess.query(UserMeta, UserGroup).filter(UserGroup.name == group_name,
                                                                  UserMeta.name == 'key').one()

            self.assertTrue([result[k] for k in (UserMeta.name, UserMeta.value, UserMeta.units)] == triple)

        finally:
            if group:
                group.remove()
                helpers.remove_unused_metadata(self.sess)

    def test_user_metadata(self):
        user_name = "testuser"
        user = None

        try:
            user = self.sess.users.create(user_name, 'rodsuser')

            # metadata collection is the right type?
            self.assertIsInstance(user.metadata, iRODSMetaCollection)

            # add three AVUs, two having the same key
            user.metadata['key0'] = iRODSMeta('key0', 'value', 'units')
            sorted_triples = sorted( [ ['key1', 'value0', 'units0'],
                                       ['key1', 'value1', 'units1']  ] )
            for m in sorted_triples:
                user.metadata.add(iRODSMeta(*m))

            # general query gives the right results?
            result_0 =  self.sess.query(UserMeta, User)\
                         .filter( User.name == user_name, UserMeta.name == 'key0').one()

            self.assertTrue( [result_0[k] for k in (UserMeta.name, UserMeta.value, UserMeta.units)]
                              == ['key0', 'value', 'units'] )

            results_1 =  self.sess.query(UserMeta, User)\
                         .filter(User.name == user_name, UserMeta.name == 'key1')

            retrieved_triples = [ [ res[k] for k in (UserMeta.name, UserMeta.value, UserMeta.units) ]
                                  for res in results_1
                                ]

            self.assertTrue( sorted_triples == sorted(retrieved_triples))

        finally:
            if user:
                user.remove()
                helpers.remove_unused_metadata(self.sess)

    def test_get_user_metadata(self):
        user_name = "testuser"
        user = None

        try:
            # create user
            user = self.sess.users.create(user_name, 'rodsuser')
            meta = user.metadata.get_all('key')

            # There should be no metadata
            self.assertEqual(len(meta), 0)
        finally:
            if user: user.remove()

    def test_add_user_metadata(self):
        user_name = "testuser"
        user = None

        try:
            # create user
            user = self.sess.users.create(user_name, 'rodsuser')

            user.metadata.add('key0', 'value0')
            user.metadata.add('key1', 'value1', 'unit1')
            user.metadata.add('key2', 'value2a', 'unit2')
            user.metadata.add('key2', 'value2b', 'unit2')

            meta0 = user.metadata.get_all('key0')
            self.assertEqual(len(meta0),1)
            self.assertEqual(meta0[0].name, 'key0')
            self.assertEqual(meta0[0].value, 'value0')

            meta1 = user.metadata.get_all('key1')
            self.assertEqual(len(meta1),1)
            self.assertEqual(meta1[0].name, 'key1')
            self.assertEqual(meta1[0].value, 'value1')
            self.assertEqual(meta1[0].units, 'unit1')

            meta2 = sorted(user.metadata.get_all('key2'), key = lambda AVU : AVU.value)
            self.assertEqual(len(meta2),2)
            self.assertEqual(meta2[0].name, 'key2')
            self.assertEqual(meta2[0].value, 'value2a')
            self.assertEqual(meta2[0].units, 'unit2')
            self.assertEqual(meta2[1].name, 'key2')
            self.assertEqual(meta2[1].value, 'value2b')
            self.assertEqual(meta2[1].units, 'unit2')

            user.metadata.remove('key1', 'value1', 'unit1')
            metadata = user.metadata.items()
            self.assertEqual(len(metadata), 3)

            user.metadata.remove('key2', 'value2a', 'unit2')
            metadata = user.metadata.items()
            self.assertEqual(len(metadata), 2)

        finally:
            if user:
                user.remove()
                helpers.remove_unused_metadata(self.sess)

if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
