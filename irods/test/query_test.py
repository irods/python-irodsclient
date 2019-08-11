#! /usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import six
import sys
import tempfile
import unittest
from datetime import datetime
from irods.models import User, Collection, DataObject, DataObjectMeta, Resource
from irods.exception import MultipleResultsFound, CAT_UNKNOWN_SPECIFIC_QUERY, CAT_INVALID_ARGUMENT
from irods.query import SpecificQuery
from irods.column import Like, Between
from irods.meta import iRODSMeta
from irods import MAX_SQL_ROWS
import irods.test.helpers as helpers
from six.moves import range as py3_range

IRODS_STATEMENT_TABLE_SIZE = 50

def remove_unused_metadata (sess) :

    from irods.message import GeneralAdminRequest, iRODSMessage
    from irods.api_number import api_number
    message_body = GeneralAdminRequest( 'rm', 'unusedAVUs', '','','','')
    req = iRODSMessage("RODS_API_REQ", msg = message_body,int_info=api_number['GENERAL_ADMIN_AN'])
    with sess.pool.get_connection() as conn:
        conn.send(req)
        response=conn.recv()
        if (response.int_info != 0): raise RuntimeError("Error removing unused AVU's")

class TestQuery(unittest.TestCase):

    Iterate_to_exhaust_statement_table = range(IRODS_STATEMENT_TABLE_SIZE + 1)

    More_than_one_batch = 2*MAX_SQL_ROWS # may need to increase if PRC default page
                                         #   size is increased beyond 500

    def setUp(self):
        self.sess = helpers.make_session()

        # test data
        self.coll_path = '/{}/home/{}/test_dir'.format(self.sess.zone, self.sess.username)
        self.obj_name = 'test1'
        self.obj_path = '{coll_path}/{obj_name}'.format(**vars(self))

        # Create test collection and (empty) test object
        self.coll = self.sess.collections.create(self.coll_path)
        self.obj = self.sess.data_objects.create(self.obj_path)

    def tearDown(self):
        '''Remove test data and close connections
        '''
        self.coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def test_collections_query(self):
        # collection query test
        result = self.sess.query(Collection.id, Collection.name).all()
        assert result.has_value(self.coll_path)


    def test_files_query(self):
        # file query test
        query = self.sess.query(
            DataObject.id, DataObject.collection_id, DataObject.name, User.name, Collection.name)

        # coverage
        for column in query.columns:
            repr(column)

        result = query.all()
        assert result.has_value(self.obj_name)


    def test_users_query(self):
        '''Lists all users and look for known usernames
        '''
        # query takes model(s) or column(s)
        # only need User.name here
        results = self.sess.query(User.name).all()

        # get user list from results
        users = [row[User.name] for row in results.rows]

        # assertions
        self.assertIn('rods', users)
        self.assertIn('public', users)


    def test_resources_query(self):
        '''Lists resources
        '''
        # query takes model(s) or column(s)
        results = self.sess.query(Resource).all()

        # check ResultSet.__str__()
        str(results)

        # get resource list from results
        resources = [row[Resource.name] for row in results.rows]

        # assertions
        self.assertIn('demoResc', resources)


    def test_query_first(self):
        # with no result
        results = self.sess.query(User.name).filter(User.name == 'boo').first()
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
        results = self.sess.query(User.name).order_by(
            User.name, order='desc').all()

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
            results = self.sess.query(User.name).order_by(
                User.name, order='moo').all()


    def test_query_with_like_condition(self):
        '''Equivalent to:
        iquest "select RESC_NAME where RESC_NAME like 'dem%'"
        '''

        query = self.sess.query(Resource).filter(Like(Resource.name, 'dem%'))
        self.assertIn('demoResc', [row[Resource.name] for row in query])


    def test_query_with_between_condition(self):
        '''Equivalent to:
        iquest "select RESC_NAME, COLL_NAME, DATA_NAME where DATA_MODIFY_TIME between '01451606400' '...'"
        '''
        session = self.sess

        start_date = datetime(2016, 1, 1, 0, 0)
        end_date = datetime.utcnow()

        query = session.query(Resource.name, Collection.name, DataObject.name)\
            .filter(Between(DataObject.modify_time, (start_date, end_date)))

        for result in query:
            res_str = '{} {}/{}'.format(result[Resource.name], result[Collection.name], result[DataObject.name])
            self.assertIn(session.zone, res_str)

    @unittest.skipIf(six.PY3, 'Test is for python2 only')
    def test_query_for_data_object_with_utf8_name_python2(self):
        filename_prefix = '_prefix_ǠǡǢǣǤǥǦǧǨǩǪǫǬǭǮǯǰǱǲǳǴǵǶǷǸ'
        _,test_file = tempfile.mkstemp(prefix=filename_prefix)
        obj_path = os.path.join(self.coll.path, os.path.basename(test_file))
        try:
            self.sess.data_objects.register(test_file, obj_path)
            results = self.sess.query(DataObject, Collection.name).filter(DataObject.path == test_file).first()
            result_logical_path = os.path.join(results[Collection.name], results[DataObject.name])
            result_physical_path = results[DataObject.path]
            self.assertEqual(result_logical_path, obj_path.decode('utf8'))
            self.assertEqual(result_physical_path, test_file.decode('utf8'))
        finally:
            self.sess.data_objects.unregister(obj_path)
            os.remove(test_file)

    @unittest.skipIf(six.PY2, 'Test is for python3 only')
    def test_query_for_data_object_with_utf8_name_python3(self):
        filename_prefix = u'_prefix_ǠǡǢǣǤǥǦǧǨǩǪǫǬǭǮǯǰǱǲǳǴǵǶǷǸ'
        _,encoded_test_file = tempfile.mkstemp(prefix=filename_prefix.encode('utf-8'))
        self.assertTrue(os.path.exists(encoded_test_file))

        test_file = encoded_test_file.decode('utf-8')
        obj_path = os.path.join(self.coll.path, os.path.basename(test_file))

        try:
            self.sess.data_objects.register(test_file, obj_path)

            results = self.sess.query(DataObject, Collection.name).filter(DataObject.path == test_file).first()
            result_logical_path = os.path.join(results[Collection.name], results[DataObject.name])
            result_physical_path = results[DataObject.path]
            self.assertEqual(result_logical_path, obj_path)
            self.assertEqual(result_physical_path, test_file)
        finally:
            self.sess.data_objects.unregister(obj_path)
            os.remove(encoded_test_file)

    class Issue_166_context:
        '''
        For [irods/python-irodsclient#166] related tests
        '''

        def __init__(self, session, coll_path='test_collection_issue_166', num_objects=8, num_avus_per_object=0):
            self.session = session
            if '/' not in coll_path:
                coll_path = '/{}/home/{}/{}'.format(self.session.zone, self.session.username, coll_path)
            self.coll_path = coll_path
            self.num_objects = num_objects
            self.test_collection = None
            self.nAVUs = num_avus_per_object

        def __enter__(self): # - prepare for context block ("with" statement)

            self.test_collection = helpers.make_test_collection( self.session, self.coll_path, obj_count=self.num_objects)
            q_params = (Collection.name, DataObject.name)

            if self.nAVUs > 0:

                # - set the AVUs on the collection's objects:
                for data_obj_path in map(lambda d:d[Collection.name]+"/"+d[DataObject.name],
                                         self.session.query(*q_params).filter(Collection.name == self.test_collection.path)):
                    data_obj = self.session.data_objects.get(data_obj_path)
                    for key in (str(x) for x in py3_range(self.nAVUs)):
                        data_obj.metadata[key] = iRODSMeta(key, "1")

                # - in subsequent test searches, match on each AVU of every data object in the collection:
                q_params += (DataObjectMeta.name,)

            # - The "with" statement receives, as context variable, a zero-arg function to build the query
            return lambda : self.session.query( *q_params ).filter( Collection.name == self.test_collection.path)

        def __exit__(self,*_): # - clean up after context block

            if self.test_collection is not None:
                self.test_collection.remove(recurse=True, force=True)

            if self.nAVUs > 0 and self.num_objects > 0:
                remove_unused_metadata(self.session)                    # delete unused AVU's

    def test_query_first__166(self):

        with self.Issue_166_context(self.sess) as buildQuery:
            for dummy_i in self.Iterate_to_exhaust_statement_table:
                buildQuery().first()

    def test_query_one__166(self):

        with self.Issue_166_context(self.sess, num_objects = self.More_than_one_batch) as buildQuery:

            for dummy_i in self.Iterate_to_exhaust_statement_table:
                query = buildQuery()
                try:
                    query.one()
                except MultipleResultsFound:
                    pass # irrelevant result

    def test_query_one_iter__166(self):

        with self.Issue_166_context(self.sess, num_objects = self.More_than_one_batch) as buildQuery:

            for dummy_i in self.Iterate_to_exhaust_statement_table:

                for dummy_row in buildQuery():
                    break # single iteration

    def test_paging_get_batches_and_check_paging__166(self):

        with self.Issue_166_context( self.sess, num_objects = 1,
                                     num_avus_per_object = 2 * self.More_than_one_batch) as buildQuery:

            pages = [b for b in buildQuery().get_batches()]
            self.assertTrue(len(pages) > 2 and len(pages[0]) < self.More_than_one_batch)

            to_compare = []

            for _ in self.Iterate_to_exhaust_statement_table:

                for batch in buildQuery().get_batches():
                    to_compare.append(batch)
                    if len(to_compare) == 2: break  #leave query unfinished, but save two pages to compare

                # - To make sure paging was done, we ensure that this "key" tuple (collName/dataName , metadataKey)
                #   is not repeated between first two pages:

                Compare_Key = lambda d: ( d[Collection.name] + "/" + d[DataObject.name],
                                          d[DataObjectMeta.name] )
                Set0 = { Compare_Key(dct) for dct in to_compare[0] }
                Set1 = { Compare_Key(dct) for dct in to_compare[1] }
                self.assertTrue(len(Set0 & Set1) == 0) # assert intersection is null set

    def test_paging_get_results__166(self):

        with self.Issue_166_context( self.sess, num_objects = self.More_than_one_batch) as buildQuery:
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
                        break # leave iteration unfinished

class TestSpecificQuery(unittest.TestCase):

    def setUp(self):
        super(TestSpecificQuery, self).setUp()
        self.session = helpers.make_session()


    def tearDown(self):
        self.session.cleanup()
        super(TestSpecificQuery, self).tearDown()


    def test_query_data_name_and_id(self):
        # make a test collection larger than MAX_SQL_ROWS (number of files)
        test_collection_size = 3*MAX_SQL_ROWS
        test_collection_path = '/{0}/home/{1}/test_collection'.format(self.session.zone, self.session.username)
        self.test_collection = helpers.make_test_collection(
            self.session, test_collection_path, obj_count=test_collection_size)

        # make specific query
        sql = "select DATA_NAME, DATA_ID from R_DATA_MAIN join R_COLL_MAIN using (COLL_ID) where COLL_NAME = '{test_collection_path}'".format(**locals())
        alias = 'list_data_name_id'
        columns = [DataObject.name, DataObject.id]
        query = SpecificQuery(self.session, sql, alias, columns)

        # register query in iCAT
        query.register()

        # run query and check results
        for i, result in enumerate(query):
            self.assertIn('test', result[DataObject.name])
            self.assertIsNotNone(result[DataObject.id])
        self.assertEqual(i, test_collection_size - 1)

        # unregister query
        query.remove()

        # remove test collection
        self.test_collection.remove(recurse=True, force=True)


    def test_query_data_name_and_id_no_columns(self):
        '''Same test as above, but without providing query columns to parse results.
        Result columns are retrieved by index 0..n
        '''

        # make a test collection larger than MAX_SQL_ROWS (number of files)
        test_collection_size = 3*MAX_SQL_ROWS
        test_collection_path = '/{0}/home/{1}/test_collection'.format(self.session.zone, self.session.username)
        self.test_collection = helpers.make_test_collection(
            self.session, test_collection_path, obj_count=test_collection_size)

        # make specific query
        sql = "select DATA_NAME, DATA_ID from R_DATA_MAIN join R_COLL_MAIN using (COLL_ID) where COLL_NAME = '{test_collection_path}'".format(**locals())
        alias = 'list_data_name_id'
        query = SpecificQuery(self.session, sql, alias)

        # register query in iCAT
        query.register()

        # run query and check results
        for i, result in enumerate(query):
            self.assertIn('test', result[0])
            self.assertIsNotNone(result[1])
        self.assertEqual(i, test_collection_size - 1)

        # unregister query
        query.remove()

        # remove test collection
        self.test_collection.remove(recurse=True, force=True)


    def test_register_query_twice(self):
        query = SpecificQuery(self.session, sql='select DATA_NAME from R_DATA_MAIN', alias='list_data_names')

        # register query
        query.register()

        # register same query again
        with self.assertRaises(CAT_INVALID_ARGUMENT) as ex:
            query.register()

        # check the error message
        self.assertEqual(str(ex.exception), 'Alias is not unique')

        # remove query
        query.remove()


    def test_list_specific_queries(self):
        query = SpecificQuery(self.session, alias='ls')

        for result in query:
            self.assertIsNotNone(result[0])             # query alias
            self.assertIn('SELECT', result[1].upper())  # query string


    def test_list_specific_queries_with_arguments(self):
        query = SpecificQuery(self.session, alias='lsl', args=['%OFFSET%'])

        for result in query:
            self.assertIsNotNone(result[0])             # query alias
            self.assertIn('SELECT', result[1].upper())  # query string


    def test_list_specific_queries_with_unknown_alias(self):
        query = SpecificQuery(self.session, alias='foo')

        with self.assertRaises(CAT_UNKNOWN_SPECIFIC_QUERY):
            res = query.get_results()
            next(res)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
