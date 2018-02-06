#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import unittest
from irods.models import Collection, DataObject
import irods.test.helpers as helpers


class TestContinueQuery(unittest.TestCase):

    def setUp(self):
        self.sess = helpers.make_session()

        # Create test collection
        self.coll_path = '/{}/home/{}/test_dir'.format(self.sess.zone, self.sess.username)
        self.obj_count = 2500
        self.coll = helpers.make_test_collection(
            self.sess, self.coll_path, self.obj_count)

    def tearDown(self):
        '''Remove test data and close connections
        '''
        self.coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def test_walk_large_collection(self):
        for current_coll, subcolls, objects in self.coll.walk():
            # check number of objects
            self.assertEqual(len(objects), self.obj_count)

            # check object names
            counter = 0
            for obj in objects:
                self.assertEqual(
                    obj.name, "test" + str(counter).zfill(6) + ".txt")
                counter += 1

    def test_files_generator(self):
        # Query for all files in test collection
        query = self.sess.query(DataObject.name, Collection.name).filter(
            Collection.name == self.coll_path)

        counter = 0

        for result in query:
            # what we should see
            object_path = self.coll_path + \
                "/test" + str(counter).zfill(6) + ".txt"

            # what we see
            result_path = "{}/{}".format(
                result[Collection.name], result[DataObject.name])

            # compare
            self.assertEqual(result_path, object_path)
            counter += 1

        # make sure we got all of them
        self.assertEqual(counter, self.obj_count)

    def test_query_offset_limit_all(self):
        # settings
        max_rows = 100
        offset = 50

        # Query should close after getting max_rows
        results = self.sess.query(DataObject.name, Collection.name).offset(
            offset).limit(max_rows).all()
        self.assertEqual(len(results), max_rows)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
