#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import unittest
from irods.models import User
from irods.exception import UserDoesNotExist, ResourceDoesNotExist
import irods.test.config as config
import irods.test.helpers as helpers


class TestAdmin(unittest.TestCase):

    '''Suite of tests on admin operations
    '''

    # test data
    new_user_name = 'bobby'
    new_user_type = 'rodsuser'
    new_user_zone = config.IRODS_SERVER_ZONE    # use remote zone when creation is supported

    def setUp(self):
        self.sess = helpers.make_session_from_config()

    def tearDown(self):
        '''Close connections
        '''
        self.sess.cleanup()

    def test_session_with_client_user(self):
        # stub
        with helpers.make_session_from_config(client_user=config.IRODS_USER_USERNAME,
                                              client_zone=config.IRODS_SERVER_ZONE) as sess:
            self.assertTrue(sess)

    def test_create_delete_local_user(self):
        # user should not be already present
        with self.assertRaises(UserDoesNotExist):
            self.sess.users.get(self.new_user_name)

        # create user
        user = self.sess.users.create(self.new_user_name, self.new_user_type)

        # assertions
        self.assertEqual(user.name, self.new_user_name)
        self.assertEqual(user.zone, config.IRODS_SERVER_ZONE)
        self.assertEqual(
            repr(user), "<iRODSUser {0} {1} {2} {3}>".format(user.id, self.new_user_name, user.type, config.IRODS_SERVER_ZONE))

        # delete user
        user.remove()

        # user should be gone
        with self.assertRaises(UserDoesNotExist):
            self.sess.users.get(self.new_user_name)

    def test_create_delete_user_zone(self):
        # user should not be already present
        with self.assertRaises(UserDoesNotExist):
            self.sess.users.get(self.new_user_name, self.new_user_zone)

        # create user
        user = self.sess.users.create(
            self.new_user_name, self.new_user_type, self.new_user_zone)

        # assertions
        self.assertEqual(user.name, self.new_user_name)
        self.assertEqual(user.zone, self.new_user_zone)

        # delete user
        user.remove()

        # user should be gone
        with self.assertRaises(UserDoesNotExist):
            self.sess.users.get(self.new_user_name, self.new_user_zone)

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
        self.sess.users.modify(
            self.new_user_name + '#' + self.new_user_zone, 'type', 'rodsadmin')

        # check type again
        row = self.sess.query(User.type).filter(
            User.name == self.new_user_name).one()
        self.assertEqual(row[User.type], 'rodsadmin')

        # delete user
        self.sess.users.remove(self.new_user_name)

        # user should be gone
        with self.assertRaises(UserDoesNotExist):
            self.sess.users.get(self.new_user_name)

    @unittest.skipIf(config.IRODS_SERVER_VERSION < (4, 0, 0), "iRODS 4+")
    def test_make_compound_resource(self):
        session = self.sess
        zone = config.IRODS_SERVER_ZONE
        username = config.IRODS_USER_USERNAME
        obj_path = '/{zone}/home/{username}/foo.txt'.format(**locals())
        dummy_str = b'blah'

        # make compound resource
        comp = session.resources.create('comp_resc', 'compound')

        # make 1st ufs resource
        resc_name = 'ufs1'
        resc_type = 'unixfilesystem'
        resc_host = config.IRODS_SERVER_HOST
        resc_path = '/tmp/' + resc_name
        ufs1 = session.resources.create(
            resc_name, resc_type, resc_host, resc_path)

        # make 2nd ufs resource
        resc_name = 'ufs2'
        resc_path = '/tmp/' + resc_name
        ufs2 = session.resources.create(
            resc_name, resc_type, resc_host, resc_path)

        # add children to compound
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

        # remove children from compound
        session.resources.remove_child(comp.name, ufs1.name)
        session.resources.remove_child(comp.name, ufs2.name)

        # remove resources
        ufs1.remove()
        ufs2.remove()
        comp.remove()

    @unittest.skipIf(config.IRODS_SERVER_VERSION < (4, 0, 0), "iRODS 4+")
    def test_resource_context_string(self):
        session = self.sess
        zone = config.IRODS_SERVER_ZONE
        username = config.IRODS_USER_USERNAME
        context = {'S3_DEFAULT_HOSTNAME': 'storage.example.com', 'S3_AUTH_FILE': '/path/to/auth/file', 'S3_STSDATE': 'date',
                   'obj_bucket': 'my_bucket', 'arch_bucket': 'test_archive', 'S3_WAIT_TIME_SEC': '1', 'S3_PROTO': 'HTTPS', 'S3_RETRY_COUNT': '3'}

        # make a resource
        resc_name = 's3archive'
        resc_type = 's3'
        resc_host = config.IRODS_SERVER_HOST
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
        if config.IRODS_SERVER_VERSION < (4, 0, 0):
            resc_type = 'unix file system'
            resc_class = 'cache'
        else:
            resc_type = 'unixfilesystem'
            resc_class = ''
        resc_host = config.IRODS_SERVER_HOST
        resc_path = '/tmp/' + resc_name
        dummy_str = b'blah'
        zone = config.IRODS_SERVER_ZONE
        username = config.IRODS_USER_USERNAME

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
            repr(resource), "<iRODSResource {0} {1} {2}>".format(resource.id, resc_name, resc_type))

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
        # make new regular user
        username = self.new_user_name
        zone = self.new_user_zone
        self.sess.users.create(self.new_user_name, self.new_user_type)

        # set password (not yet supported)
        test_password = '@?$#'
        with self.assertRaises(ValueError):
            self.sess.users.modify(username, 'password', test_password)

        # delete user
        self.sess.users.remove(self.new_user_name)

        # user should be gone
        with self.assertRaises(UserDoesNotExist):
            self.sess.users.get(self.new_user_name)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
