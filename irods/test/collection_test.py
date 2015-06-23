#! /usr/bin/env python
import os
import sys
if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest
from irods.session import iRODSSession
import irods.test.config as config
import irods.test.helpers as helpers


class TestCollection(unittest.TestCase):
    test_coll_path = '/{0}/home/{1}/test_dir'.format(
        config.IRODS_SERVER_ZONE, config.IRODS_USER_USERNAME)

    def setUp(self):
        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)

        self.coll = self.sess.collections.create(self.test_coll_path)

    def tearDown(self):
        """ Delete the test collection after each test """
        self.coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def test_get_collection(self):
        # path = "/tempZone/home/rods"
        coll = self.sess.collections.get(self.test_coll_path)
        self.assertEquals(self.test_coll_path, coll.path)

    # def test_new_collection(self):
    #    self.assertEquals(self.coll.name, 'test_dir')

    def test_append_to_collection(self):
        """ Append a new file to the collection"""
        pass

    def test_remove_from_collection(self):
        """ Delete a file from a collection """
        pass

    def test_update_in_collection(self):
        """ Modify a file in a collection """
        pass

    def test_rename_collection(self):
        # test args
        args = {'collection': self.test_coll_path,
                'old_name': 'foo',
                'new_name': 'bar'}

        # make collection
        path = "{collection}/{old_name}".format(**args)
        coll = helpers.make_collection(self.sess, path)

        # get collection id
        saved_id = coll.id

        # rename coll
        new_path = "{collection}/{new_name}".format(**args)
        self.sess.collections.move(path, new_path)

        # get updated collection
        coll = self.sess.collections.get(new_path)

        # compare ids
        self.assertEqual(coll.id, saved_id)

        # remove collection
        coll.remove(recurse=True, force=True)

    def test_move_coll_to_coll(self):
        # test args
        args = {'base_collection': self.test_coll_path,
                'collection1': 'foo',
                'collection2': 'bar'}

        # make collection1 and collection2 in base collection
        path1 = "{base_collection}/{collection1}".format(**args)
        coll1 = helpers.make_collection(self.sess, path1)
        path2 = "{base_collection}/{collection2}".format(**args)
        coll2 = helpers.make_collection(self.sess, path2)

        # get collection2's id
        saved_id = coll2.id

        # move collection2 into collection1
        self.sess.collections.move(path2, path1)

        # get updated collection
        path2 = "{base_collection}/{collection1}/{collection2}".format(**args)
        coll2 = self.sess.collections.get(path2)

        # compare ids
        self.assertEqual(coll2.id, saved_id)

        # remove collection
        coll1.remove(recurse=True, force=True)

    # def test_delete_collection(self):
    #    pass

if __name__ == "__main__":
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
