#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import socket
import shutil
import unittest
from irods.meta import iRODSMetaCollection
from irods.exception import CollectionDoesNotExist
from irods.models import Collection, DataObject
import irods.test.helpers as helpers
import irods.keywords as kw
from six.moves import range


class TestCollection(unittest.TestCase):

    def setUp(self):
        self.sess = helpers.make_session()
        self.test_coll_path = '/{}/home/{}/test_dir'.format(self.sess.zone, self.sess.username)

        self.test_coll = self.sess.collections.create(self.test_coll_path)


    def tearDown(self):
        """ Delete the test collection after each test """
        self.test_coll.remove(recurse=True, force=True)
        self.sess.cleanup()


    def test_get_collection(self):
        # path = "/tempZone/home/rods"
        coll = self.sess.collections.get(self.test_coll_path)
        self.assertEqual(self.test_coll_path, coll.path)


    def test_append_to_collection(self):
        """ Append a new file to the collection"""
        pass


    def test_remove_from_collection(self):
        """ Delete a file from a collection """
        pass


    def test_update_in_collection(self):
        """ Modify a file in a collection """
        pass


    def test_create_recursive_collection(self):
        # make path with recursion
        root_coll_path = self.test_coll_path + "/recursive/collection/test"
        self.sess.collections.create(root_coll_path, recurse=True)

        #confirm col create
        coll = self.sess.collections.get(root_coll_path)
        self.assertEqual(root_coll_path, coll.path)

        # delete test collection
        coll.remove(force=True)

        # confirm delete
        with self.assertRaises(CollectionDoesNotExist):
            self.sess.collections.get(root_coll_path)

    def test_remove_deep_collection(self):
        # depth = 100
        depth = 20  # placeholder
        root_coll_path = self.test_coll_path + "/deep_collection"

        # make test collection
        helpers.make_deep_collection(
            self.sess, root_coll_path, depth=depth, objects_per_level=1, object_content=None)

        # delete test collection
        self.sess.collections.remove(root_coll_path, recurse=True, force=True)

        # confirm delete
        with self.assertRaises(CollectionDoesNotExist):
            self.sess.collections.get(root_coll_path)


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
        coll.move(new_path)
        # self.sess.collections.move(path, new_path)

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


    def test_repr_coll(self):
        coll_name = self.test_coll.name.encode('utf-8')
        coll_id = self.test_coll.id

        self.assertEqual(
            repr(self.test_coll), "<iRODSCollection {coll_id} {coll_name}>".format(**locals()))


    def test_walk_collection_topdown(self):
        depth = 20

        # files that will be ceated in each subcollection
        filenames = ['foo', 'bar', 'baz']

        # make nested collections
        coll_path = self.test_coll_path
        for d in range(depth):
            # create subcollection with files
            coll_path += '/sub' + str(d)
            helpers.make_collection(self.sess, coll_path, filenames)

        # now walk nested collections
        colls = self.test_coll.walk()
        current_coll_name = self.test_coll.name
        for d in range(depth + 1):
            # get next result
            collection, subcollections, data_objects = next(colls)

            # check collection name
            self.assertEqual(collection.name, current_coll_name)

            # check subcollection name
            if d < depth:
                sub_coll_name = 'sub' + str(d)
                self.assertEqual(sub_coll_name, subcollections[0].name)
            else:
                # last coll has no subcolls
                self.assertListEqual(subcollections, [])

            # check data object names
            for data_object in data_objects:
                self.assertIn(data_object.name, filenames)

            # iterate
            current_coll_name = sub_coll_name

        # that should be it
        with self.assertRaises(StopIteration):
            next(colls)


    def test_walk_collection(self):
        depth = 20

        # files that will be ceated in each subcollection
        filenames = ['foo', 'bar', 'baz']

        # make nested collections
        coll_path = self.test_coll_path
        for d in range(depth):
            # create subcollection with files
            coll_path += '/sub' + str(d)
            helpers.make_collection(self.sess, coll_path, filenames)

        # now walk nested collections
        colls = self.test_coll.walk(topdown=False)
        sub_coll_name = ''
        for d in range(depth - 1, -2, -1):
            # get next result
            collection, subcollections, data_objects = next(colls)

            # check collection name
            if d >= 0:
                coll_name = 'sub' + str(d)
                self.assertEqual(collection.name, coll_name)
            else:
                # root collection
                self.assertEqual(collection.name, self.test_coll.name)

            # check subcollection name
            if d < depth - 1:
                self.assertEqual(sub_coll_name, subcollections[0].name)
            else:
                # last coll has no subcolls
                self.assertListEqual(subcollections, [])

            # check data object names
            for data_object in data_objects:
                self.assertIn(data_object.name, filenames)

            # iterate
            sub_coll_name = coll_name

        # that should be it
        with self.assertRaises(StopIteration):
            next(colls)

    def test_collection_metadata(self):
        self.assertIsInstance(self.test_coll.metadata, iRODSMetaCollection)


    def test_register_collection(self):
        if self.sess.host not in ('localhost', socket.gethostname()):
            self.skipTest('Requires access to server-side file(s)')

        # test vars
        file_count = 10
        dir_name = 'register_test_dir'
        dir_path = os.path.join('/tmp', dir_name)
        coll_path = '{}/{}'.format(self.test_coll.path, dir_name)

        # make test dir
        helpers.make_flat_test_dir(dir_path, file_count)

        # register test dir
        self.sess.collections.register(dir_path, coll_path)

        # confirm collection presence
        coll = self.sess.collections.get(coll_path)

        # confirm object count in collection
        query = self.sess.query().count(DataObject.id).filter(Collection.name == coll_path)
        obj_count = next(query.get_results())[DataObject.id]
        self.assertEqual(file_count, int(obj_count))

        # remove coll but leave directory on disk
        coll.unregister()

        # delete test dir
        shutil.rmtree(dir_path)


    def test_register_collection_with_checksums(self):
        if self.sess.host not in ('localhost', socket.gethostname()):
            self.skipTest('Requires access to server-side file(s)')

        # test vars
        file_count = 10
        dir_name = 'register_test_dir'
        dir_path = os.path.join('/tmp', dir_name)
        coll_path = '{}/{}'.format(self.test_coll.path, dir_name)

        # make test dir
        helpers.make_flat_test_dir(dir_path, file_count)

        # register test dir
        options = {kw.VERIFY_CHKSUM_KW: ''}
        self.sess.collections.register(dir_path, coll_path, **options)

        # confirm collection presence
        coll = self.sess.collections.get(coll_path)

        # confirm object count in collection
        query = self.sess.query().count(DataObject.id).filter(Collection.name == coll_path)
        obj_count = next(query.get_results())[DataObject.id]
        self.assertEqual(file_count, int(obj_count))

        # confirm object checksums
        objs = next(coll.walk())[2]
        for obj in objs:
            # don't use obj.path (aka logical path)
            phys_path = obj.replicas[0].path
            digest = helpers.compute_sha256_digest(phys_path)
            self.assertEqual(obj.checksum, "sha2:{}".format(digest))

        # remove coll but leave directory on disk
        coll.unregister()

        # delete test dir
        shutil.rmtree(dir_path)


if __name__ == "__main__":
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
