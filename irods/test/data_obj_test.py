#! /usr/bin/env python
import os
import sys
if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest
from irods.models import Collection, DataObject
from irods.session import iRODSSession
from irods.exception import DataObjectDoesNotExist, CollectionDoesNotExist
from irods.column import Column, Criterion
import irods.test.config as config
import irods.test.helpers as helpers


class TestDataObjOps(unittest.TestCase):

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

    def test_rename_obj(self):
        # test args
        collection = self.coll_path
        old_name = 'foo'
        new_name = 'bar'

        # make object in test collection
        path = "{collection}/{old_name}".format(**locals())
        obj = helpers.make_object(self.sess, path)

        # get object id
        saved_id = obj.id

        # rename object
        new_path = "{collection}/{new_name}".format(**locals())
        self.sess.data_objects.move(path, new_path)

        # get updated object
        obj = self.sess.data_objects.get(new_path)

        # compare ids
        self.assertEqual(obj.id, saved_id)

        # remove object
        self.sess.data_objects.unlink(new_path)

    def test_move_obj_to_coll(self):
        # test args
        collection = self.coll_path
        new_coll_name = 'my_coll'
        file_name = 'foo'

        # make object in test collection
        path = "{collection}/{file_name}".format(**locals())
        obj = helpers.make_object(self.sess, path)

        # get object id
        saved_id = obj.id

        # make new collection and move object to it
        new_coll_path = "{collection}/{new_coll_name}".format(**locals())
        new_coll = helpers.make_collection(self.sess, new_coll_path)
        self.sess.data_objects.move(path, new_coll_path)

        # get new object id
        new_path = "{collection}/{new_coll_name}/{file_name}".format(**locals())
        obj = self.sess.data_objects.get(new_path)

        # compare ids
        self.assertEqual(obj.id, saved_id)

        # remove new collection
        new_coll.remove(recurse=True, force=True)

    def test_invalid_get(self):
        # bad paths
        path_with_invalid_file = self.coll_path + '/hamsalad'
        path_with_invalid_coll = self.coll_path + '/hamsandwich/foo'

        with self.assertRaises(DataObjectDoesNotExist):
            obj = self.sess.data_objects.get(path_with_invalid_file)

        with self.assertRaises(DataObjectDoesNotExist):
            obj = self.sess.data_objects.get(path_with_invalid_coll)

    def test_force_unlink(self):
        collection = self.coll_path
        filename = 'test_force_unlink.txt'
        file_path = '{collection}/{filename}'.format(**locals())
        
        # make object
        obj = helpers.make_object(self.sess, file_path)
        
        # force remove object
        obj.unlink(force=True)

        # should be gone
        with self.assertRaises(DataObjectDoesNotExist):
            obj = self.sess.data_objects.get(file_path)

        # make sure it's not in the trash either
        conditions = [DataObject.name == filename, 
                      Criterion('like', Collection.name, "/dev/trash/%%")]
        query = self.sess.query(DataObject.id, DataObject.name, Collection.name).filter(*conditions)
        results = query.all()
        self.assertEqual(len(results), 0)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
