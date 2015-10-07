#! /usr/bin/env python
import os, sys
import unittest
from irods.models import User
from irods.session import iRODSSession
import irods.test.config as config
import irods.test.helpers as helpers


class TestAccess(unittest.TestCase):

    def setUp(self):
        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)

        # Create dummy test collection
        self.coll_path = '/{0}/home/{1}/test_dir'.format(config.IRODS_SERVER_ZONE, config.IRODS_USER_USERNAME)
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
        user = self.sess.users.get(config.IRODS_USER_USERNAME, config.IRODS_SERVER_ZONE)

        # make object in test collection
        path = "{collection}/{filename}".format(**locals())
        obj = helpers.make_object(self.sess, path)

        # get object
        obj = self.sess.data_objects.get(path)

        # get object's ACL
        acl = self.sess.permissions.get(path)[0]

        # checks
        self.assertEqual(acl.data_id, obj.id)
        self.assertEqual(acl.name, 'own')
        self.assertEqual(acl.user_id, user.id)
        self.assertEqual(acl.user_name, user.name)

        # remove object
        self.sess.data_objects.unlink(path)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()