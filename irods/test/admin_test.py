#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import unittest
from irods.models import User
from irods.exception import UserDoesNotExist, ResourceDoesNotExist
from irods.session import iRODSSession
from irods.resource import iRODSResource
import irods.test.helpers as helpers


class TestAdmin(unittest.TestCase):
    '''Suite of tests on admin operations
    '''

    # test data
    new_user_name = 'bobby'
    new_user_type = 'rodsuser'


    def setUp(self):
        self.sess = helpers.make_session()


    def tearDown(self):
        '''Close connections
        '''
        self.sess.cleanup()


    def test_create_delete_local_user(self):
        # user should not be already present
        with self.assertRaises(UserDoesNotExist):
            self.sess.users.get(self.new_user_name)

        # create user
        user = self.sess.users.create(self.new_user_name, self.new_user_type)

        # assertions
        self.assertEqual(user.name, self.new_user_name)
        self.assertEqual(user.zone, self.sess.zone)
        self.assertEqual(
            repr(user), "<iRODSUser {id} {name} {type} {zone}>".format(**vars(user)))

        # delete user
        user.remove()

        # user should be gone
        with self.assertRaises(UserDoesNotExist):
            self.sess.users.get(self.new_user_name)


    def test_create_delete_user_zone(self):
        # user should not be already present
        with self.assertRaises(UserDoesNotExist):
            self.sess.users.get(self.new_user_name, self.sess.zone)

        # create user
        user = self.sess.users.create(
            self.new_user_name, self.new_user_type, self.sess.zone)

        # assertions
        self.assertEqual(user.name, self.new_user_name)
        self.assertEqual(user.zone, self.sess.zone)

        # delete user
        user.remove()

        # user should be gone
        with self.assertRaises(UserDoesNotExist):
            self.sess.users.get(self.new_user_name, self.sess.zone)


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
        with self.assertRaises(UserDoesNotExist):
            self.sess.users.get(self.new_user_name)


    def test_modify_user_type_with_zone(self):
        # make new regular user
        self.sess.users.create(self.new_user_name, self.new_user_type)

        # check type
        row = self.sess.query(User.type).filter(
            User.name == self.new_user_name).one()
        self.assertEqual(row[User.type], self.new_user_type)

        # change type to rodsadmin
        self.sess.users.modify('{}#{}'.format(self.new_user_name, self.sess.zone), 'type', 'rodsadmin')

        # check type again
        row = self.sess.query(User.type).filter(
            User.name == self.new_user_name).one()
        self.assertEqual(row[User.type], 'rodsadmin')

        # delete user
        self.sess.users.remove(self.new_user_name)

        # user should be gone
        with self.assertRaises(UserDoesNotExist):
            self.sess.users.get(self.new_user_name)


    def test_make_compound_resource(self):
        if self.sess.server_version < (4, 0, 0):
            self.skipTest('For iRODS 4+')

        session = self.sess
        zone = self.sess.zone
        username = self.sess.username
        obj_path = '/{zone}/home/{username}/foo.txt'.format(**locals())
        dummy_str = b'blah'

        # make compound resource
        comp = session.resources.create('comp_resc', 'compound')

        # make 1st ufs resource
        resc_name = 'ufs1'
        resc_type = 'unixfilesystem'
        resc_host = self.sess.host
        resc_path = '/tmp/' + resc_name
        ufs1 = session.resources.create(
            resc_name, resc_type, resc_host, resc_path)

        # make 2nd ufs resource
        resc_name = 'ufs2'
        resc_path = '/tmp/' + resc_name
        ufs2 = session.resources.create(
            resc_name, resc_type, resc_host, resc_path)

        # add children to compound resource
        session.resources.add_child(comp.name, ufs1.name, 'archive')
        session.resources.add_child(comp.name, ufs2.name, 'cache')

        # create object on compound resource
        obj = session.data_objects.create(obj_path, comp.name)

        # write to object
        with obj.open('w+') as obj_desc:
            obj_desc.write(dummy_str)

        # refresh object
        obj = session.data_objects.get(obj_path)

        # check that we have 2 replicas
        self.assertEqual(len(obj.replicas), 2)

        # remove object
        obj.unlink(force=True)

        # remove children from compound resource
        session.resources.remove_child(comp.name, ufs1.name)
        session.resources.remove_child(comp.name, ufs2.name)

        # remove resources
        ufs1.remove()
        ufs2.remove()
        comp.remove()


    def test_get_resource_children(self):
        if self.sess.server_version < (4, 0, 0):
            self.skipTest('For iRODS 4+')

        session = self.sess
        username = self.sess.username

        # make compound resource
        compound_resource = session.resources.create('comp_resc', 'compound')

        # make 1st ufs resource
        resc_name = 'ufs1'
        resc_type = 'unixfilesystem'
        resc_host = self.sess.host
        resc_path = '/tmp/' + resc_name
        ufs1 = session.resources.create(
            resc_name, resc_type, resc_host, resc_path)

        # make 2nd ufs resource
        resc_name2 = 'ufs2'
        resc_path = '/tmp/' + resc_name2
        ufs2 = session.resources.create(
            resc_name2, resc_type, resc_host, resc_path)

        # add children to compound resource
        session.resources.add_child(compound_resource.name, ufs1.name, 'archive')
        session.resources.add_child(compound_resource.name, ufs2.name, 'cache')

        # confirm number of children
        self.assertEqual(len(compound_resource.children), 2)

        # assertions on children
        for child in compound_resource.children:
            self.assertIsInstance(child, iRODSResource)
            self.assertIn(child.name, [resc_name, resc_name2])
            self.assertEqual(child.type, resc_type)
            self.assertEqual(child.location, resc_host)

            if session.server_version >= (4, 2, 0):
                self.assertIn(child.parent_context, ['archive', 'cache'])

        # remove children from compound resource
        session.resources.remove_child(compound_resource.name, ufs1.name)
        session.resources.remove_child(compound_resource.name, ufs2.name)

        # remove resources
        ufs1.remove()
        ufs2.remove()
        compound_resource.remove()


    def test_resource_context_string(self):
        if self.sess.server_version < (4, 0, 0):
            self.skipTest('For iRODS 4+')

        session = self.sess
        zone = self.sess.zone
        username = self.sess.username
        context = {'S3_DEFAULT_HOSTNAME': 'storage.example.com', 'S3_AUTH_FILE': '/path/to/auth/file', 'S3_STSDATE': 'date',
                   'obj_bucket': 'my_bucket', 'arch_bucket': 'test_archive', 'S3_WAIT_TIME_SEC': '1', 'S3_PROTO': 'HTTPS', 'S3_RETRY_COUNT': '3'}

        # make a resource
        resc_name = 's3archive'
        resc_type = 's3'
        resc_host = self.sess.host
        resc_path = '/nobucket'
        s3 = session.resources.create(
            resc_name, resc_type, resc_host, resc_path, context)

        # verify context fields
        self.assertEqual(context, s3.context_fields)

        # modify resource context
        context['S3_PROTO'] = 'HTTP'
        s3 = session.resources.modify(s3.name, 'context', context)

        # verify context fields again
        self.assertEqual(context, s3.context_fields)

        # remove resource
        s3.remove()


    def test_make_ufs_resource(self):
        # test data
        resc_name = 'temporary_test_resource'
        if self.sess.server_version < (4, 0, 0):
            resc_type = 'unix file system'
            resc_class = 'cache'
        else:
            resc_type = 'unixfilesystem'
            resc_class = ''
        resc_host = self.sess.host
        resc_path = '/tmp/' + resc_name
        dummy_str = b'blah'
        zone = self.sess.zone
        username = self.sess.username

        coll_path = '/{zone}/home/{username}/test_dir'.format(**locals())
        obj_name = 'test1'
        obj_path = '{coll_path}/{obj_name}'.format(**locals())

        # make new resource
        self.sess.resources.create(
            resc_name, resc_type, resc_host, resc_path, resource_class=resc_class)

        # try invalid params
        with self.assertRaises(ResourceDoesNotExist):
            resource = self.sess.resources.get(resc_name, zone='invalid_zone')

        # retrieve resource
        resource = self.sess.resources.get(resc_name)

        # assertions
        self.assertEqual(resource.name, resc_name)
        self.assertEqual(
            repr(resource), "<iRODSResource {id} {name} {type}>".format(**vars(resource)))

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

        # test delete resource
        self.sess.resources.remove(resc_name, test=True)

        # delete resource for good
        self.sess.resources.remove(resc_name)


    def test_set_user_password(self):
        # make a new user
        username = self.new_user_name
        zone = self.sess.zone
        self.sess.users.create(self.new_user_name, self.new_user_type)

        # make a really horrible password
        new_password = '''abc123!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~Z'''
        self.sess.users.modify(username, 'password', new_password)

        # open a session as the new user
        with iRODSSession(host=self.sess.host,
                          port=self.sess.port,
                          user=username,
                          password=new_password,
                          zone=self.sess.zone) as session:

            # do something that connects to the server
            session.users.get(username)

        # delete new user
        self.sess.users.remove(self.new_user_name)

        # user should be gone
        with self.assertRaises(UserDoesNotExist):
            self.sess.users.get(self.new_user_name)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
