#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import unittest
import time
import uuid
from datetime import datetime, timezone
from irods.models import (
    User,
    UserMeta,
    Resource,
    ResourceMeta,
    Collection,
    CollectionMeta,
    DataObject,
    DataObjectMeta,
    RuleExec,
)

from tempfile import NamedTemporaryFile
from irods.exception import (
    MultipleResultsFound,
    CAT_UNKNOWN_SPECIFIC_QUERY,
    CAT_INVALID_ARGUMENT,
)
from irods import MAX_SQL_ROWS
import irods.client_configuration as config
from irods.column import Like, NotLike, Between, In
import irods.keywords as kw
from irods.meta import iRODSMeta
from irods.query import SpecificQuery
from irods.rule import Rule
import irods.test.helpers as helpers
from irods.test.helpers import irods_shared_reg_resc_vault

IRODS_STATEMENT_TABLE_SIZE = 50


def rows_returned(query):
    return len(list(query))


class TestQuery(unittest.TestCase):

    Iterate_to_exhaust_statement_table = range(IRODS_STATEMENT_TABLE_SIZE + 1)

    More_than_one_batch = 2 * MAX_SQL_ROWS  # may need to increase if PRC default page
    #   size is increased beyond 500

    register_resc = ""

    @classmethod
    def setUpClass(cls):
        with helpers.make_session() as sess:
            resource_name = helpers.get_register_resource(sess)
            if resource_name:
                cls.register_resc = resource_name

    @classmethod
    def tearDownClass(cls):
        with helpers.make_session() as sess:
            try:
                if cls.register_resc:
                    sess.resources.get(cls.register_resc).remove()
            except Exception as e:
                print(
                    "Could not remove resc {!r} due to: {} ".format(
                        cls.register_resc, e
                    ),
                    file=sys.stderr,
                )

    def setUp(self):
        self.sess = helpers.make_session()

        # test data
        self.coll_path = "/{}/home/{}/test_dir".format(
            self.sess.zone, self.sess.username
        )
        self.obj_name = "test1"
        self.case_sensitive_obj_name1 = "caseSENSITIVEobject"
        self.case_sensitive_obj_name2 = "CASEsensitiveOBJECT"
        self.obj_path = "{coll_path}/{obj_name}".format(**vars(self))
        self.case_sensitive_obj_path1 = "{coll_path}/{case_sensitive_obj_name1}".format(
            **vars(self)
        )
        self.case_sensitive_obj_path2 = "{coll_path}/{case_sensitive_obj_name2}".format(
            **vars(self)
        )

        # Create test collection and (empty) test object
        self.coll = self.sess.collections.create(self.coll_path)
        for obj in [
            self.obj_path,
            self.case_sensitive_obj_path1,
            self.case_sensitive_obj_path2,
        ]:
            self.sess.data_objects.create(obj)

    def tearDown(self):
        """Remove test data and close connections"""
        self.coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def test_collections_query(self):
        # collection query test
        result = self.sess.query(Collection.id, Collection.name).all()
        assert result.has_value(self.coll_path)

    def test_files_query(self):
        # file query test
        query = self.sess.query(
            DataObject.id,
            DataObject.collection_id,
            DataObject.name,
            User.name,
            Collection.name,
        )

        # coverage
        for column in query.columns:
            repr(column)

        result = query.all()
        assert result.has_value(self.obj_name)

    def test_files_query_case_sensitive(self):
        # This tests that GenQueries are case-sensitive by default.

        # Exact filter tests

        result1 = (
            self.sess.query(DataObject.name)
            .filter(DataObject.name == self.case_sensitive_obj_name1)
            .all()
        )
        self.assertTrue(result1.has_value(self.case_sensitive_obj_name1))
        self.assertEqual(len(result1), 1)

        result2 = (
            self.sess.query(DataObject.name)
            .filter(DataObject.name == str.lower(self.case_sensitive_obj_name1))
            .all()
        )
        self.assertEqual(len(result2), 0)

        result3 = (
            self.sess.query(DataObject.name)
            .filter(DataObject.name == str.upper(self.case_sensitive_obj_name1))
            .all()
        )
        self.assertEqual(len(result3), 0)

        # Wildcard filter (Like/NotLike) tests

        search_expression = "%{}%".format(self.case_sensitive_obj_name1[1:-1])

        result4 = (
            self.sess.query(DataObject.name)
            .filter(Like(DataObject.name, search_expression))
            .all()
        )
        self.assertTrue(result4.has_value(self.case_sensitive_obj_name1))
        self.assertEqual(len(result4), 1)

        result5 = (
            self.sess.query(DataObject.name)
            .filter(Like(DataObject.name, str.lower(search_expression)))
            .all()
        )
        self.assertEqual(len(result5), 0)

        result6 = (
            self.sess.query(DataObject.name)
            .filter(Like(DataObject.name, str.upper(search_expression)))
            .all()
        )
        self.assertEqual(len(result6), 0)

        result7 = (
            self.sess.query(DataObject.name)
            .filter(Collection.name == self.coll_path)
            .filter(NotLike(DataObject.name, search_expression))
            .all()
        )
        self.assertTrue(result7.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result7), 2)

        result8 = (
            self.sess.query(DataObject.name)
            .filter(Collection.name == self.coll_path)
            .filter(NotLike(DataObject.name, str.lower(search_expression)))
            .all()
        )
        self.assertTrue(result8.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result8.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result8), 3)

        result9 = (
            self.sess.query(DataObject.name)
            .filter(Collection.name == self.coll_path)
            .filter(NotLike(DataObject.name, str.upper(search_expression)))
            .all()
        )
        self.assertTrue(result9.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result9.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result9), 3)

        # IN tests

        result10 = (
            self.sess.query(DataObject.name)
            .filter(Collection.name == self.coll_path)
            .filter(In(DataObject.name, [self.case_sensitive_obj_name1]))
            .all()
        )
        self.assertTrue(result10.has_value(self.case_sensitive_obj_name1))
        self.assertEqual(len(result10), 1)

        result11 = (
            self.sess.query(DataObject.name)
            .filter(Collection.name == self.coll_path)
            .filter(In(DataObject.name, [str.lower(self.case_sensitive_obj_name1)]))
            .all()
        )
        self.assertEqual(len(result11), 0)

        result12 = (
            self.sess.query(DataObject.name)
            .filter(Collection.name == self.coll_path)
            .filter(In(DataObject.name, [str.upper(self.case_sensitive_obj_name1)]))
            .all()
        )
        self.assertEqual(len(result12), 0)

        # BETWEEN tests

        # TODO(#600): Uncomment these lines and/or make a new test when database flavor can be detected.
        # The resultset for BETWEEN queries can differ from database to database.

        # result13 = self.sess.query(DataObject.name).filter(
        #    Collection.name == self.coll_path).filter(
        #    Between(DataObject.name, [self.case_sensitive_obj_name1,
        #                              self.case_sensitive_obj_name1 + "_"])).all()
        # self.assertTrue(result13.has_value(self.case_sensitive_obj_name1))
        # self.assertEqual(len(result13), 1)

        # result14 = self.sess.query(DataObject.name).filter(
        #    Collection.name == self.coll_path).filter(
        #    Between(DataObject.name, [str.lower(self.case_sensitive_obj_name1),
        #                              str.lower(self.case_sensitive_obj_name1) + "_"])).all()
        # self.assertEqual(len(result14), 0)

        # result15 = self.sess.query(DataObject.name).filter(
        #    Collection.name == self.coll_path).filter(
        #    Between(DataObject.name, [str.upper(self.case_sensitive_obj_name1),
        #                              str.upper(self.case_sensitive_obj_name1) + "_"])).all()
        # self.assertEqual(len(result15), 0)

    def test_files_query_case_insensitive(self):
        # This tests that GenQueries are case-insensitive when the case_sensitive
        # option is set to false.

        # Single exact filter tests

        result1 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(DataObject.name == self.case_sensitive_obj_name1)
            .all()
        )
        self.assertTrue(result1.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result1.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result1), 2)

        result2 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(DataObject.name == str.lower(self.case_sensitive_obj_name1))
            .all()
        )
        self.assertTrue(result2.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result2.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result2), 2)

        result3 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(DataObject.name == str.upper(self.case_sensitive_obj_name1))
            .all()
        )
        self.assertTrue(result3.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result3.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result3), 2)

        # Single wildcard filter (Like, NotLike) tests

        search_expression = "%{}%".format(self.case_sensitive_obj_name1[1:-1])

        result4 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(Like(DataObject.name, search_expression))
            .all()
        )
        self.assertTrue(result4.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result4.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result4), 2)

        result5 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(Like(DataObject.name, str.lower(search_expression)))
            .all()
        )
        self.assertTrue(result5.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result5.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result5), 2)

        result6 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(Like(DataObject.name, str.upper(search_expression)))
            .all()
        )
        self.assertTrue(result6.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result6.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result6), 2)

        result7 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(Collection.name == self.coll_path)
            .filter(NotLike(DataObject.name, search_expression))
            .all()
        )
        self.assertFalse(result7.has_value(self.case_sensitive_obj_name1))
        self.assertFalse(result7.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result7), 1)

        result8 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(Collection.name == self.coll_path)
            .filter(NotLike(DataObject.name, str.lower(search_expression)))
            .all()
        )
        self.assertFalse(result8.has_value(self.case_sensitive_obj_name1))
        self.assertFalse(result8.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result8), 1)

        result9 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(Collection.name == self.coll_path)
            .filter(NotLike(DataObject.name, str.upper(search_expression)))
            .all()
        )
        self.assertFalse(result9.has_value(self.case_sensitive_obj_name1))
        self.assertFalse(result9.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result9), 1)

        # IN tests

        result10 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(Collection.name == self.coll_path)
            .filter(In(DataObject.name, [self.case_sensitive_obj_name1]))
            .all()
        )
        self.assertTrue(result10.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result10.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result10), 2)

        result11 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(Collection.name == self.coll_path)
            .filter(In(DataObject.name, [str.lower(self.case_sensitive_obj_name1)]))
            .all()
        )
        self.assertTrue(result11.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result11.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result11), 2)

        result12 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(Collection.name == self.coll_path)
            .filter(In(DataObject.name, [str.upper(self.case_sensitive_obj_name1)]))
            .all()
        )
        self.assertTrue(result12.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result12.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result12), 2)

        # BETWEEN tests

        result13 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(Collection.name == self.coll_path)
            .filter(
                Between(
                    DataObject.name,
                    [
                        self.case_sensitive_obj_name1,
                        self.case_sensitive_obj_name1 + "_",
                    ],
                )
            )
            .all()
        )
        self.assertTrue(result13.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result13.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result13), 2)

        result14 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(Collection.name == self.coll_path)
            .filter(
                Between(
                    DataObject.name,
                    [
                        str.lower(self.case_sensitive_obj_name1),
                        str.lower(self.case_sensitive_obj_name1) + "_",
                    ],
                )
            )
            .all()
        )
        self.assertTrue(result14.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result14.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result14), 2)

        result15 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(Collection.name == self.coll_path)
            .filter(
                Between(
                    DataObject.name,
                    [
                        str.upper(self.case_sensitive_obj_name1),
                        str.upper(self.case_sensitive_obj_name1) + "_",
                    ],
                )
            )
            .all()
        )
        self.assertTrue(result15.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result15.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result15), 2)

        # Multiple filter tests - when a case-insensitive query has multiple filters,
        # they should all be case-insensitive.

        result16 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(Like(DataObject.name, search_expression))
            .filter(Collection.name == self.coll_path)
            .all()
        )
        self.assertTrue(result16.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result16.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result16), 2)

        result17 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(Like(DataObject.name, str.lower(search_expression)))
            .filter(Collection.name == str.lower(self.coll_path))
            .all()
        )
        self.assertTrue(result17.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result17.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result17), 2)

        result18 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(Like(DataObject.name, str.upper(search_expression)))
            .filter(Collection.name == str.upper(self.coll_path))
            .all()
        )
        self.assertTrue(result18.has_value(self.case_sensitive_obj_name1))
        self.assertTrue(result18.has_value(self.case_sensitive_obj_name2))
        self.assertEqual(len(result18), 2)

        # All previous queries in this function expect a match. This query should not match.
        result19 = (
            self.sess.query(DataObject.name, case_sensitive=False)
            .filter(Like(DataObject.name, "THIS_SHOULD_NOT_MATCH"))
            .all()
        )
        self.assertEqual(len(result19), 0)

    def test_users_query(self):
        """Lists all users and look for known usernames"""
        # query takes model(s) or column(s)
        # only need User.name here
        results = self.sess.query(User.name).all()

        # get user list from results
        users = [row[User.name] for row in results.rows]

        # assertions
        self.assertIn("rods", users)
        self.assertIn("public", users)

    def test_resources_query(self):
        """Lists resources"""
        # query takes model(s) or column(s)
        results = self.sess.query(Resource).all()

        # check ResultSet.__str__()
        str(results)

        # get resource list from results
        resources = [row[Resource.name] for row in results.rows]

        # assertions
        self.assertIn("demoResc", resources)

    def test_query_first(self):
        # with no result
        results = self.sess.query(User.name).filter(User.name == "boo").first()
        self.assertIsNone(results)

        # with result
        results = self.sess.query(User.name).first()
        self.assertEqual(len(results), 1)

    def test_query_one(self):
        # with multiple results
        with self.assertRaises(MultipleResultsFound):
            results = self.sess.query(User.name).one()

    def test_query_wrong_type(self):
        with self.assertRaises(TypeError):
            query = self.sess.query(str())

    def test_query_order_by(self):
        # query for user names
        results = self.sess.query(User.name).order_by(User.name).all()

        # get user names from results
        user_names = []
        for result in results:
            user_names.append(result[User.name])

        # make copy before sorting
        original = list(user_names)

        # check that list was already sorted
        user_names.sort()
        self.assertEqual(user_names, original)

    def test_query_order_by_desc(self):
        # query for user names
        results = self.sess.query(User.name).order_by(User.name, order="desc").all()

        # get user names from results
        user_names = []
        for result in results:
            user_names.append(result[User.name])

        # make copy before sorting
        original = list(user_names)

        # check that list was already sorted
        user_names.sort(reverse=True)
        self.assertEqual(user_names, original)

    def test_query_order_by_invalid_param(self):
        with self.assertRaises(ValueError):
            results = self.sess.query(User.name).order_by(User.name, order="moo").all()

    def test_query_order_by_col_not_in_result__183(self):
        test_collection_size = 8
        test_collection_path = "/{0}/home/{1}/testcoln_for_col_not_in_result".format(
            self.sess.zone, self.sess.username
        )
        c1 = c2 = None
        try:
            c1 = helpers.make_test_collection(
                self.sess, test_collection_path + "1", obj_count=test_collection_size
            )
            c2 = helpers.make_test_collection(
                self.sess, test_collection_path + "2", obj_count=test_collection_size
            )
            d12 = [
                sorted([d.id for d in c.data_objects])
                for c in sorted((c1, c2), key=lambda c: c.id)
            ]
            query = (
                self.sess.query(DataObject)
                .filter(Like(Collection.name, test_collection_path + "_"))
                .order_by(Collection.id)
            )
            q12 = list(map(lambda res: res[DataObject.id], query))
            self.assertTrue(
                d12[0] + d12[1]
                == sorted(q12[:test_collection_size])
                + sorted(q12[test_collection_size:])
            )
        finally:
            if c1:
                c1.remove(recurse=True, force=True)
            if c2:
                c2.remove(recurse=True, force=True)

    def test_query_with_like_condition(self):
        """Equivalent to:
        iquest "select RESC_NAME where RESC_NAME like 'dem%'"
        """

        query = self.sess.query(Resource).filter(Like(Resource.name, "dem%"))
        self.assertIn("demoResc", [row[Resource.name] for row in query])

    def test_query_with_between_condition(self):
        """Equivalent to:
        iquest "select RESC_NAME, COLL_NAME, DATA_NAME where DATA_MODIFY_TIME between '01451606400' '...'"
        """
        session = self.sess

        start_date = datetime(2016, 1, 1, 0, 0)
        end_date = datetime.now(timezone.utc)

        query = session.query(Resource.name, Collection.name, DataObject.name).filter(
            Between(DataObject.modify_time, (start_date, end_date))
        )

        for result in query:
            res_str = "{} {}/{}".format(
                result[Resource.name], result[Collection.name], result[DataObject.name]
            )
            self.assertIn(session.zone, res_str)

    def test_query_with_in_condition(self):
        collection = self.coll_path
        filename = "test_query_id_in_list.txt"
        file_path = "{collection}/{filename}".format(**locals())
        obj1 = helpers.make_object(self.sess, file_path + "-1")
        obj2 = helpers.make_object(self.sess, file_path + "-2")
        ids = [x.id for x in (obj1, obj2)]
        for number in range(3):  # slice for empty(:0), first(:1) or both(:2)
            search_tuple = ids[:number] if number >= 1 else [0] + ids[:number]
            q = self.sess.query(DataObject.name).filter(In(DataObject.id, search_tuple))
            self.assertEqual(number, rows_returned(q))

    def test_simultaneous_multiple_AVU_joins(self):
        objects = []
        decoys = []
        try:
            collection = self.coll_path
            filename = "test_multiple_AVU_joins"
            file_path = "{collection}/{filename}".format(**locals())
            for x in range(3, 9):
                obj = helpers.make_object(
                    self.sess, file_path + "-{}".format(x)
                )  # with metadata
                objects.append(obj)
                obj.metadata.add("A_meta", "1{}".format(x))
                obj.metadata.add("B_meta", "2{}".format(x))
                decoys.append(
                    helpers.make_object(self.sess, file_path + "-dummy{}".format(x))
                )  # without metadata
            self.assertTrue(len(objects) > 0)

            # -- test simple repeat of same column --
            q = (
                self.sess.query(DataObject, DataObjectMeta)
                .filter(DataObjectMeta.name == "A_meta", DataObjectMeta.value < "20")
                .filter(DataObjectMeta.name == "B_meta", DataObjectMeta.value >= "20")
            )
            self.assertTrue(rows_returned(q) == len(objects))

            # -- test no-stomp of previous filter --
            self.assertTrue(
                ("B_meta", "28")
                in [(x.name, x.value) for x in objects[-1].metadata.items()]
            )
            q = (
                self.sess.query(DataObject, DataObjectMeta)
                .filter(DataObjectMeta.name == "B_meta")
                .filter(DataObjectMeta.value < "28")
                .filter(DataObjectMeta.name == "B_meta")
                .filter(Like(DataObjectMeta.value, "2_"))
            )
            self.assertTrue(rows_returned(q) == len(objects) - 1)

            # -- test multiple AVU's by same attribute name --
            objects[-1].metadata.add("B_meta", "29")
            q = (
                self.sess.query(DataObject, DataObjectMeta)
                .filter(DataObjectMeta.name == "B_meta")
                .filter(DataObjectMeta.value == "28")
                .filter(DataObjectMeta.name == "B_meta")
                .filter(DataObjectMeta.value == "29")
            )
            self.assertTrue(rows_returned(q) == 1)
        finally:
            for x in objects + decoys:
                x.unlink(force=True)
            helpers.remove_unused_metadata(self.sess)

    def test_query_on_AVU_times(self):
        test_collection_path = "/{zone}/home/{user}/test_collection".format(
            zone=self.sess.zone, user=self.sess.username
        )
        testColl = helpers.make_test_collection(
            self.sess, test_collection_path, obj_count=1
        )
        testData = testColl.data_objects[0]
        testResc = self.sess.resources.get("demoResc")
        testUser = self.sess.users.get(self.sess.username)
        objects = {"r": testResc, "u": testUser, "c": testColl, "d": testData}
        object_IDs = {sfx: obj.id for sfx, obj in objects.items()}
        tables = {
            "r": (Resource, ResourceMeta),
            "u": (User, UserMeta),
            "d": (DataObject, DataObjectMeta),
            "c": (Collection, CollectionMeta),
        }
        try:
            str_number_incr = lambda str_numbers: str(
                1 + max([0] + [int(n) if n.isdigit() else 0 for n in str_numbers])
            )
            AVU_unique_incr = lambda obj, suffix="": (
                "a_" + suffix,
                "v_" + suffix,
                str_number_incr(avu.units for avu in obj.metadata.items()),
            )
            before = datetime.now(timezone.utc)
            time.sleep(1.5)
            for suffix, obj in objects.items():
                obj.metadata.add(*AVU_unique_incr(obj, suffix))
            after = datetime.now(timezone.utc)
            for suffix, tblpair in tables.items():
                self.sess.query(*tblpair).filter(
                    tblpair[1].modify_time <= after
                ).filter(tblpair[1].modify_time > before).filter(
                    tblpair[0].id == object_IDs[suffix]
                ).one()
                self.sess.query(*tblpair).filter(
                    tblpair[1].create_time <= after
                ).filter(tblpair[1].create_time > before).filter(
                    tblpair[0].id == object_IDs[suffix]
                ).one()
        finally:
            for obj in objects.values():
                for avu in obj.metadata.items():
                    obj.metadata.remove(avu)
            testColl.remove(recurse=True, force=True)
            helpers.remove_unused_metadata(self.sess)

    def test_multiple_criteria_on_one_column_name(self):
        # Remove the column skips when irods/irods #8574 is resolved.
        skipped_columns = {DataObject.map_id, Collection.map_id, DataObject.status, DataObject.type, DataObject.collection_id}
        collection = self.coll_path
        filename = "test_multiple_AVU_joins"
        file_path = "{collection}/{filename}".format(**locals())
        objects = []
        nobj = 0
        for x in range(3, 9):
            nobj += 2
            obj1 = helpers.make_object(self.sess, file_path + "-{}".format(x))
            obj2 = helpers.make_object(self.sess, file_path + "-dummy{}".format(x))
            objects.extend([obj1, obj2])
        self.assertTrue(nobj > 0 and len(objects) == nobj)
        q = self.sess.query(Collection, DataObject, *{-col for col in skipped_columns})
        dummy_test = [
            d
            for d in q
            if d[DataObject.name][-1:] != "8" and d[DataObject.name][-7:-1] == "-dummy"
        ]
        self.assertTrue(len(dummy_test) > 0)
        q = (
            q.filter(Like(DataObject.name, "%-dummy_"))
            .filter(Collection.name == collection)
            .filter(DataObject.name != (filename + "-dummy8"))
        )
        results = [r[DataObject.name] for r in q]
        self.assertTrue(len(results) == len(dummy_test))

    def common_dir_or_vault_info(self):
        register_opts = {}
        dir_ = None
        if self.register_resc:
            dir_ = irods_shared_reg_resc_vault()
            register_opts[kw.RESC_NAME_KW] = self.register_resc
        if not (dir_) and helpers.irods_session_host_local(self.sess):
            dir_ = tempfile.gettempdir()
        if not dir_:
            return ()
        else:
            return (dir_, register_opts)

    # view/change this line in text editors under own risk:
    FILENAME_PREFIX = "_prefix_ǠǡǢǣǤǥǦǧǨǩǪǫǬǭǮǯǰǱǲǳǴǵǶǷǸ"

    def test_query_for_data_object_with_utf8_name_python3(self):
        reg_info = self.common_dir_or_vault_info()
        if not reg_info:
            self.skipTest(
                "server is non-localhost and no common path exists for object registration"
            )
        (dir_, resc_option) = reg_info

        def python34_unicode_mkstemp(prefix, dir=None, open_mode=0o777):
            file_path = os.path.join(
                (dir or os.environ.get("TMPDIR") or "/tmp"),
                prefix + "-" + str(uuid.uuid1()),
            )
            encoded_file_path = file_path.encode("utf-8")
            return (
                os.open(encoded_file_path, os.O_CREAT | os.O_RDWR, mode=open_mode),
                encoded_file_path,
            )

        fd = None
        filename_prefix = (
            "_prefix_"
            "\u01e0\u01e1\u01e2\u01e3\u01e4\u01e5\u01e6\u01e7\u01e8\u01e9\u01ea\u01eb\u01ec\u01ed\u01ee\u01ef"
            "\u01f0\u01f1\u01f2\u01f3\u01f4\u01f5\u01f6\u01f7\u01f8"
        )  # make more visible/changeable in VIM
        self.assertEqual(self.FILENAME_PREFIX, filename_prefix)
        (fd, encoded_test_file) = (
            tempfile.mkstemp(
                dir=dir_.encode("utf-8"), prefix=filename_prefix.encode("utf-8")
            )
            if sys.version_info >= (3, 5)
            else python34_unicode_mkstemp(dir=dir_, prefix=filename_prefix)
        )
        self.assertTrue(os.path.exists(encoded_test_file))
        test_file = encoded_test_file.decode("utf-8")
        obj_path = os.path.join(self.coll.path, os.path.basename(test_file))
        results = None
        try:
            self.sess.data_objects.register(test_file, obj_path, **resc_option)
            results = list(
                self.sess.query(DataObject, Collection.name).filter(
                    DataObject.path == test_file
                )
            )
            if results:
                results = results[0]
                result_logical_path = os.path.join(
                    results[Collection.name], results[DataObject.name]
                )
                result_physical_path = results[DataObject.path]
                self.assertEqual(result_logical_path, obj_path)
                self.assertEqual(result_physical_path, test_file)
        finally:
            if results:
                self.sess.data_objects.unregister(obj_path)
            if fd is not None:
                os.close(fd)
            os.remove(encoded_test_file)

    class Issue_166_context:
        """
        For [irods/python-irodsclient#166] related tests
        """

        def __init__(
            self,
            session,
            coll_path="test_collection_issue_166",
            num_objects=8,
            num_avus_per_object=0,
        ):
            self.session = session
            if "/" not in coll_path:
                coll_path = "/{}/home/{}/{}".format(
                    self.session.zone, self.session.username, coll_path
                )
            self.coll_path = coll_path
            self.num_objects = num_objects
            self.test_collection = None
            self.nAVUs = num_avus_per_object

        def __enter__(self):  # - prepare for context block ("with" statement)

            self.test_collection = helpers.make_test_collection(
                self.session, self.coll_path, obj_count=self.num_objects
            )
            q_params = (Collection.name, DataObject.name)

            if self.nAVUs > 0:

                # - set the AVUs on the collection's objects:
                for data_obj_path in map(
                    lambda d: d[Collection.name] + "/" + d[DataObject.name],
                    self.session.query(*q_params).filter(
                        Collection.name == self.test_collection.path
                    ),
                ):
                    data_obj = self.session.data_objects.get(data_obj_path)
                    for key in (str(x) for x in range(self.nAVUs)):
                        data_obj.metadata[key] = iRODSMeta(key, "1")

                # - in subsequent test searches, match on each AVU of every data object in the collection:
                q_params += (DataObjectMeta.name,)

            # - The "with" statement receives, as context variable, a zero-arg function to build the query
            return lambda: self.session.query(*q_params).filter(
                Collection.name == self.test_collection.path
            )

        def __exit__(self, *_):  # - clean up after context block

            if self.test_collection is not None:
                self.test_collection.remove(recurse=True, force=True)

            if self.nAVUs > 0 and self.num_objects > 0:
                helpers.remove_unused_metadata(self.session)  # delete unused AVU's

    def test_query_first__166(self):

        with self.Issue_166_context(self.sess) as buildQuery:
            for dummy_i in self.Iterate_to_exhaust_statement_table:
                buildQuery().first()

    def test_query_one__166(self):

        with self.Issue_166_context(
            self.sess, num_objects=self.More_than_one_batch
        ) as buildQuery:

            for dummy_i in self.Iterate_to_exhaust_statement_table:
                query = buildQuery()
                try:
                    query.one()
                except MultipleResultsFound:
                    pass  # irrelevant result

    def test_query_one_iter__166(self):

        with self.Issue_166_context(
            self.sess, num_objects=self.More_than_one_batch
        ) as buildQuery:

            for dummy_i in self.Iterate_to_exhaust_statement_table:

                for dummy_row in buildQuery():
                    break  # single iteration

    def test_paging_get_batches_and_check_paging__166(self):

        with self.Issue_166_context(
            self.sess, num_objects=1, num_avus_per_object=2 * self.More_than_one_batch
        ) as buildQuery:

            pages = [b for b in buildQuery().get_batches()]
            self.assertTrue(len(pages) > 2 and len(pages[0]) < self.More_than_one_batch)

            to_compare = []

            for _ in self.Iterate_to_exhaust_statement_table:

                for batch in buildQuery().get_batches():
                    to_compare.append(batch)
                    if len(to_compare) == 2:
                        break  # leave query unfinished, but save two pages to compare

                # - To make sure paging was done, we ensure that this "key" tuple (collName/dataName , metadataKey)
                #   is not repeated between first two pages:

                Compare_Key = lambda d: (
                    d[Collection.name] + "/" + d[DataObject.name],
                    d[DataObjectMeta.name],
                )
                Set0 = {Compare_Key(dct) for dct in to_compare[0]}
                Set1 = {Compare_Key(dct) for dct in to_compare[1]}
                self.assertTrue(
                    len(Set0 & Set1) == 0
                )  # assert intersection is null set

    def test_paging_get_results__166(self):

        with self.Issue_166_context(
            self.sess, num_objects=self.More_than_one_batch
        ) as buildQuery:
            batch_size = 0
            for result_set in buildQuery().get_batches():
                batch_size = len(result_set)
                break

            self.assertTrue(0 < batch_size < self.More_than_one_batch)

            for dummy_iter in self.Iterate_to_exhaust_statement_table:
                iters = 0
                for dummy_row in buildQuery().get_results():
                    iters += 1
                    if iters == batch_size - 1:
                        break  # leave iteration unfinished

    def test_rules_query__267(self):
        unique = "Testing prc #267: queryable rule objects"
        with NamedTemporaryFile(mode="w") as rfile:
            rfile.write(
                """f() {{ delay('<EF>1m</EF>') {{ writeLine('serverLog','{unique}') }} }}\n"""
                """OUTPUT null\n""".format(**locals())
            )
            rfile.flush()
            ## create a delayed rule we can query against
            myrule = Rule(self.sess, rule_file=rfile.name)
            myrule.execute()
        qu = self.sess.query(RuleExec.id).filter(
            Like(RuleExec.frequency, "%1m%"),
            Like(RuleExec.name, "%{unique}%".format(**locals())),
        )
        results = [row for row in qu]
        self.assertEqual(1, len(results))
        if results:
            Rule(self.sess).remove_by_id(results[0][RuleExec.id])

    def test_utf8_equality_in_query__issue_442(self):
        name = "prefix-\u1000-suffix"
        self.sess.data_objects.create("{}/{}".format(self.coll_path, name))
        query = self.sess.query(DataObject).filter(
            DataObject.name == name.encode("utf8"),
            DataObject.collection_id == self.coll.id,
        )
        self.assertEqual(1, len(list(query)))

    def test_not_like_operator__issue_443(self):
        name_search_pattern = "%_issue_443.non_matching"
        query = self.sess.query(DataObject).filter(
            NotLike(DataObject.name, name_search_pattern),
            DataObject.collection_id == self.coll.id,
        )
        self.assertEqual(3, len(list(query)))

    def test_negating_columns_in_genquery1_results__issue_755(self):
        columns_to_negate = {Collection.map_id, DataObject.map_id, DataObject.status, DataObject.type, DataObject.collection_id}
        columns_to_negate_D = columns_to_negate & set(DataObject._columns)
        columns_to_negate_C = columns_to_negate & set(Collection._columns)
        cases = { (Collection, DataObject): columns_to_negate,
                  (Collection,): columns_to_negate_C,
                  (DataObject,): columns_to_negate_D, }

        for requested,intersect in cases.items():
            q = self.sess.query(*requested, *{-col for col in columns_to_negate}).limit(1)
            row = list(q.all())[0]

            # assert that columns_to_negate members don't appear in result
            self.assertFalse(columns_to_negate & row.keys())

            # Remove the if/continue when irods/irods #8574 is resolved.
            if self.sess.server_version > (5,0,0) and len(requested) > 1:
                continue

            # Re-assert the positive space: that the sets of negated columns are in fact both
            # (1) nonzero length, and
            # (2) present in the results when not explicitly negated.
            self.assertTrue(intersect)
            q = self.sess.query(*requested).limit(1)
            row = list(q.all())[0]
            self.assertEqual(columns_to_negate & row.keys(), intersect)

    def test_set_query_limit__issue_712(self):
        # Test requires that 0 < num_limited_results < num_total_objects.
        num_limited_results = 4
        num_total_objects = num_limited_results + 6
        data_objs = []
        try:
            # Create a number of data objects.
            for name in range(num_total_objects):
                data_objs.append(self.sess.data_objects.create(f'{self.coll_path}/issue_712_obj{name}'))

            # Test a query limit via configuration.
            with config.loadlines(
                entries=[dict(setting="genquery1.irods_query_limit", value=num_limited_results)]
            ):
                limited_results = list(self.sess.query(DataObject.id).filter(Like(DataObject.name, '%issue_712_obj%')).all())
                self.assertEqual(num_limited_results, len(limited_results))

            # Test the query limit is no longer in effect.
            non_limited_results = list(self.sess.query(DataObject.id).filter(Like(DataObject.name, '%issue_712_obj%')).all())
            self.assertEqual(num_total_objects, len(non_limited_results))
        finally:
            for d in data_objs:
                d.unlink(force=True)


class TestSpecificQuery(unittest.TestCase):

    def setUp(self):
        super(TestSpecificQuery, self).setUp()
        self.session = helpers.make_session()

    def tearDown(self):
        self.session.cleanup()
        super(TestSpecificQuery, self).tearDown()

    def test_query_data_name_and_id(self):
        # make a test collection larger than MAX_SQL_ROWS (number of files)
        test_collection_size = 3 * MAX_SQL_ROWS
        test_collection_path = "/{0}/home/{1}/test_collection".format(
            self.session.zone, self.session.username
        )
        self.test_collection = helpers.make_test_collection(
            self.session, test_collection_path, obj_count=test_collection_size
        )

        # make specific query
        sql = "select DATA_NAME, DATA_ID from R_DATA_MAIN join R_COLL_MAIN using (COLL_ID) where COLL_NAME = '{test_collection_path}'".format(
            **locals()
        )
        alias = "list_data_name_id"
        columns = [DataObject.name, DataObject.id]
        query = SpecificQuery(self.session, sql, alias, columns)

        # register query in iCAT
        query.register()

        # run query and check results
        for i, result in enumerate(query):
            self.assertIn("test", result[DataObject.name])
            self.assertIsNotNone(result[DataObject.id])
        self.assertEqual(i, test_collection_size - 1)

        # unregister query
        query.remove()

        # remove test collection
        self.test_collection.remove(recurse=True, force=True)

    def test_query_data_name_and_id_no_columns(self):
        """Same test as above, but without providing query columns to parse results.
        Result columns are retrieved by index 0..n
        """

        # make a test collection larger than MAX_SQL_ROWS (number of files)
        test_collection_size = 3 * MAX_SQL_ROWS
        test_collection_path = "/{0}/home/{1}/test_collection".format(
            self.session.zone, self.session.username
        )
        self.test_collection = helpers.make_test_collection(
            self.session, test_collection_path, obj_count=test_collection_size
        )

        # make specific query
        sql = "select DATA_NAME, DATA_ID from R_DATA_MAIN join R_COLL_MAIN using (COLL_ID) where COLL_NAME = '{test_collection_path}'".format(
            **locals()
        )
        alias = "list_data_name_id"
        query = SpecificQuery(self.session, sql, alias)

        # register query in iCAT
        query.register()

        # run query and check results
        for i, result in enumerate(query):
            self.assertIn("test", result[0])
            self.assertIsNotNone(result[1])
        self.assertEqual(i, test_collection_size - 1)

        # unregister query
        query.remove()

        # remove test collection
        self.test_collection.remove(recurse=True, force=True)

    def test_register_query_twice(self):
        query = SpecificQuery(
            self.session,
            sql="select DATA_NAME from R_DATA_MAIN",
            alias="list_data_names",
        )

        # register query
        query.register()

        # register same query again
        with self.assertRaises(CAT_INVALID_ARGUMENT) as ex:
            query.register()

        # check the error message
        self.assertEqual(str(ex.exception), "Alias is not unique")

        # remove query
        query.remove()

    def test_list_specific_queries(self):
        query = SpecificQuery(self.session, alias="ls")

        for result in query:
            self.assertIsNotNone(result[0])  # query alias
            self.assertIn("SELECT", result[1].upper())  # query string

    def test_list_specific_queries_with_arguments(self):
        query = SpecificQuery(self.session, alias="lsl", args=["%OFFSET%"])

        for result in query:
            self.assertIsNotNone(result[0])  # query alias
            self.assertIn("SELECT", result[1].upper())  # query string

    def test_list_specific_queries_with_unknown_alias(self):
        query = SpecificQuery(self.session, alias="foo")

        with self.assertRaises(CAT_UNKNOWN_SPECIFIC_QUERY):
            res = query.get_results()
            next(res)


if __name__ == "__main__":
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath("../.."))
    unittest.main()
