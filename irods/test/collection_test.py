#! /usr/bin/env python

from datetime import datetime, timezone
import os
import sys
import socket
import shutil
import unittest
import time
from irods.meta import iRODSMetaCollection
from irods.exception import CollectionDoesNotExist
from irods.models import Collection, DataObject
import irods.test.helpers as helpers
import irods.keywords as kw
from irods.test.helpers import my_function_name, unique_name
from irods.collection import iRODSCollection

RODSUSER = "nonadmin"


class TestCollection(unittest.TestCase):

    class WrongUserType(RuntimeError):
        pass

    @classmethod
    def setUpClass(cls):
        adm = helpers.make_session()
        if adm.users.get(adm.username).type != "rodsadmin":
            raise cls.WrongUserType(
                "Must be an iRODS admin to run tests in class {0.__name__}".format(cls)
            )
        cls.logins = helpers.iRODSUserLogins(adm)
        cls.logins.create_user(RODSUSER, "abc123")

    @classmethod
    def tearDownClass(cls):
        # As in Python 3.8 and previous, Python 3.9.19 will react badly to leaving out the following del statement during test runs. Although
        # as of 3.9.19 the segmentation fault no longer occurs, we still get an unsuccessful destruct, so the __del__ call in cls.logins
        # fails to do all of the work for proper test teardown. This happens because the object is being garbage collected at a point in time
        # when the Python interpreter is finalizing.
        del cls.logins

    def setUp(self):
        self.sess = helpers.make_session()

        self.test_coll_path = "/{}/home/{}/test_dir".format(
            self.sess.zone, self.sess.username
        )
        self.test_coll = self.sess.collections.create(self.test_coll_path)

    def tearDown(self):
        """Delete the test collection after each test"""
        self.test_coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def test_get_collection(self):
        # path = "/tempZone/home/rods"
        coll = self.sess.collections.get(self.test_coll_path)
        self.assertEqual(self.test_coll_path, coll.path)

    def test_irods_collection_information(self):
        coll = self.sess.collections.get(self.test_coll_path)
        self.assertIsNotNone(coll.create_time)
        self.assertIsNotNone(coll.modify_time)
        self.assertFalse(coll.inheritance)
        self.assertIsNotNone(coll.owner_name)
        self.assertIsNotNone(coll.owner_zone)

    def test_append_to_collection(self):
        """Append a new file to the collection"""
        pass

    def test_remove_from_collection(self):
        """Delete a file from a collection"""
        pass

    def test_update_in_collection(self):
        """Modify a file in a collection"""
        pass

    def test_create_recursive_collection(self):
        # make path with recursion
        root_coll_path = self.test_coll_path + "/recursive/collection/test"
        self.sess.collections.create(root_coll_path, recurse=True)

        # confirm col create
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
            self.sess,
            root_coll_path,
            depth=depth,
            objects_per_level=1,
            object_content=None,
        )

        # delete test collection
        self.sess.collections.remove(root_coll_path, recurse=True, force=True)

        # confirm delete
        with self.assertRaises(CollectionDoesNotExist):
            self.sess.collections.get(root_coll_path)

    def test_rename_collection(self):
        # test args
        args = {"collection": self.test_coll_path, "old_name": "foo", "new_name": "bar"}

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
        args = {
            "base_collection": self.test_coll_path,
            "collection1": "foo",
            "collection2": "bar",
        }

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
        coll_name = self.test_coll.name
        coll_id = self.test_coll.id

        self.assertEqual(
            repr(self.test_coll),
            "<iRODSCollection {coll_id} {coll_name}>".format(**locals()),
        )

    def test_walk_collection_topdown(self):
        depth = 20

        # files that will be ceated in each subcollection
        filenames = ["foo", "bar", "baz"]

        # make nested collections
        coll_path = self.test_coll_path
        for d in range(depth):
            # create subcollection with files
            coll_path += "/sub" + str(d)
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
                sub_coll_name = "sub" + str(d)
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
        filenames = ["foo", "bar", "baz"]

        # make nested collections
        coll_path = self.test_coll_path
        for d in range(depth):
            # create subcollection with files
            coll_path += "/sub" + str(d)
            helpers.make_collection(self.sess, coll_path, filenames)

        # now walk nested collections
        colls = self.test_coll.walk(topdown=False)
        sub_coll_name = ""
        for d in range(depth - 1, -2, -1):
            # get next result
            collection, subcollections, data_objects = next(colls)

            # check collection name
            if d >= 0:
                coll_name = "sub" + str(d)
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
        tmp_dir = helpers.irods_shared_tmp_dir()
        loc_server = self.sess.host in ("localhost", socket.gethostname())
        if not (tmp_dir) and not (loc_server):
            self.skipTest("Requires access to server-side file(s)")

        # test vars
        file_count = 10
        dir_name = "register_test_dir"
        dir_path = os.path.join((tmp_dir or "/tmp"), dir_name)
        coll_path = "{}/{}".format(self.test_coll.path, dir_name)

        # make test dir
        helpers.make_flat_test_dir(dir_path, file_count)

        # register test dir
        self.sess.collections.register(dir_path, coll_path)

        # confirm collection presence
        coll = self.sess.collections.get(coll_path)

        # confirm object count in collection
        query = (
            self.sess.query().count(DataObject.id).filter(Collection.name == coll_path)
        )
        obj_count = next(query.get_results())[DataObject.id]
        self.assertEqual(file_count, int(obj_count))

        # remove coll but leave directory on disk
        coll.unregister()

        # delete test dir
        shutil.rmtree(dir_path)

    def test_register_collection_with_checksums(self):
        tmp_dir = helpers.irods_shared_tmp_dir()
        loc_server = self.sess.host in ("localhost", socket.gethostname())
        if not (tmp_dir) and not (loc_server):
            self.skipTest("Requires access to server-side file(s)")

        # test vars
        file_count = 10
        dir_name = "register_test_dir_with_chksums"
        dir_path = os.path.join((tmp_dir or "/tmp"), dir_name)
        coll_path = "{}/{}".format(self.test_coll.path, dir_name)

        # make test dir
        helpers.make_flat_test_dir(dir_path, file_count)

        # register test dir
        options = {kw.VERIFY_CHKSUM_KW: ""}
        self.sess.collections.register(dir_path, coll_path, **options)

        # confirm collection presence
        coll = self.sess.collections.get(coll_path)

        # confirm object count in collection
        query = (
            self.sess.query().count(DataObject.id).filter(Collection.name == coll_path)
        )
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

    def test_collection_with_trailing_slash__323(self):
        Home = helpers.home_collection(self.sess)
        subcoll, dataobj = [
            unique_name(my_function_name(), time.time()) for x in range(2)
        ]
        subcoll_fullpath = "{}/{}".format(Home, subcoll)
        subcoll_unnormalized = subcoll_fullpath + "/"
        try:
            # Test create and exists with trailing slashes.
            self.sess.collections.create(subcoll_unnormalized)
            c1 = self.sess.collections.get(subcoll_unnormalized)
            c2 = self.sess.collections.get(subcoll_fullpath)
            self.assertEqual(c1.id, c2.id)
            self.assertTrue(self.sess.collections.exists(subcoll_unnormalized))

            # Test data put to unnormalized collection name.
            with open(dataobj, "wb") as f:
                f.write(b"hello")
            self.sess.data_objects.put(dataobj, subcoll_unnormalized)
            self.assertEqual(
                self.sess.query(DataObject)
                .filter(DataObject.name == dataobj)
                .one()[DataObject.collection_id],
                c1.id,
            )
        finally:
            if self.sess.collections.exists(subcoll_fullpath):
                self.sess.collections.remove(subcoll_fullpath, recurse=True, force=True)
            if os.path.exists(dataobj):
                os.unlink(dataobj)

    def test_concatenation__323(self):
        coll = iRODSCollection.normalize_path("/zone/", "/home/", "/dan//", "subdir///")
        self.assertEqual(coll, "/zone/home/dan/subdir")

    def test_object_paths_with_dot_and_dotdot__323(self):

        normalize = iRODSCollection.normalize_path
        session = self.sess
        home = helpers.home_collection(session)

        # Test requirement for collection names to be absolute
        with self.assertRaises(iRODSCollection.AbsolutePathRequired):
            normalize("../public", enforce_absolute=True)

        # Test '.' and double slashes
        public_home = normalize(home, "..//public/.//")
        self.assertEqual(public_home, "/{sess.zone}/home/public".format(sess=session))

        # Test that '..' cancels last nontrival path element
        subpath = normalize(home, "./collA/coll2/./../collB")
        self.assertEqual(subpath, home + "/collA/collB")

        # Test multiple '..'
        home1 = normalize("/zone", "holmes", "public/../..", "home", "user")
        self.assertEqual(home1, "/zone/home/user")
        home2 = normalize("/zone", "holmes", "..", "home", "public", "..", "user")
        self.assertEqual(home2, "/zone/home/user")

    def test_update_mtime_of_collection_using_touch_operation_as_non_admin__525(self):
        user_session = self.logins.session_for_user(RODSUSER)

        # Capture mtime of the home collection.
        home_collection_path = helpers.home_collection(user_session)
        collection = user_session.collections.get(home_collection_path)
        old_mtime = collection.modify_time

        # Set the mtime to an earlier time.
        new_mtime = 1400000000
        user_session.collections.touch(
            home_collection_path, seconds_since_epoch=new_mtime
        )

        # Compare mtimes for correctness.
        collection = user_session.collections.get(home_collection_path)
        self.assertEqual(
            datetime.fromtimestamp(new_mtime, timezone.utc), collection.modify_time
        )
        self.assertGreater(old_mtime, collection.modify_time)

    def test_touch_operation_does_not_create_new_collections__525(self):
        user_session = self.logins.session_for_user(RODSUSER)

        # The collection should not exist.
        home_collection = helpers.home_collection(user_session)
        collection_path = "{home_collection}/test_touch_operation_does_not_create_new_collections__525".format(
            **locals()
        )
        with self.assertRaises(CollectionDoesNotExist):
            user_session.collections.get(collection_path)

        # Show the touch operation throws an exception if the target collection
        # does not exist.
        with self.assertRaises(CollectionDoesNotExist):
            user_session.collections.touch(collection_path)

        # Show the touch operation did not create a new collection.
        with self.assertRaises(CollectionDoesNotExist):
            user_session.collections.get(collection_path)

    def test_touch_operation_does_not_work_when_given_a_data_object__525(self):
        try:
            user_session = self.logins.session_for_user(RODSUSER)
            home_collection = helpers.home_collection(user_session)

            # Create a data object.
            data_object_path = "{home_collection}/test_touch_operation_does_not_work_when_given_a_data_object__525.txt".format(
                **locals()
            )
            self.assertFalse(user_session.data_objects.exists(data_object_path))
            user_session.data_objects.touch(data_object_path)
            self.assertTrue(user_session.data_objects.exists(data_object_path))

            # Show the touch operation for collections throws an exception when
            # given a path pointing to a data object.
            with self.assertRaises(CollectionDoesNotExist):
                user_session.collections.touch(data_object_path)

        finally:
            user_session.data_objects.unlink(data_object_path, force=True)

    def test_touch_operation_ignores_unsupported_options__525(self):
        user_session = self.logins.session_for_user(RODSUSER)

        home_collection = helpers.home_collection(user_session)
        path = "{home_collection}/test_touch_operation_ignores_unsupported_options__525".format(
            **locals()
        )

        try:
            # Capture mtime of the home collection.
            collection = user_session.collections.create(path)
            old_mtime = collection.modify_time

            # Capture the current time.
            time.sleep(2)  # Guarantees the mtime is different.
            new_mtime = int(time.time())

            # The touch API for the iRODS server will attempt to create a new data object
            # if the "no_create" option is set to false. The PRC's collection interface will
            # ignore that option if passed.
            #
            # The following arguments don't make sense for collections and will also be ignored.
            #
            #   - replica_number
            #   - leaf_resource_name
            #
            # They are included to prove the PRC handles them appropriately (i.e. unsupported
            # parameters are removed from the request).
            user_session.collections.touch(
                path,
                no_create=False,
                replica_number=525,
                seconds_since_epoch=new_mtime,
                leaf_resource_name="ufs525",
            )

            # Compare mtimes for correctness.
            collection = user_session.collections.get(path)
            self.assertEqual(
                datetime.fromtimestamp(int(new_mtime), timezone.utc),
                collection.modify_time,
            )

        finally:
            if collection:
                user_session.collections.remove(path, recurse=True, force=True)

    def test_subcollections_member_excludes_root_collection__571(self):

        root_coll = self.sess.collections.get("/")

        # Assert that none of the root collection's immediate children (as listed in the object's
        # 'subcollections' property) point to the root subcollection.
        self.assertEqual(root_coll.path, "/")
        self.assertEqual([], [_ for _ in root_coll.subcollections if _.path == "/"])


if __name__ == "__main__":
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath("../.."))
    unittest.main()
