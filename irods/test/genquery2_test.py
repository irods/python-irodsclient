import unittest

import irods.test.helpers as helpers


class TestGenQuery2(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.sess = helpers.make_session()

        if self.sess.server_version < (4, 3, 2):
            self.skipTest(
                'GenQuery2 is not available by default in iRODS before v4.3.2.')

        self.coll_path_a = '/{}/home/{}/test_query2_coll_a'.format(
            self.sess.zone, self.sess.username)
        self.coll_path_b = '/{}/home/{}/test_query2_coll_b'.format(
            self.sess.zone, self.sess.username)
        self.sess.collections.create(self.coll_path_a)
        self.sess.collections.create(self.coll_path_b)

    @classmethod
    def tearDownClass(self):
        '''Remove test data and close connections
        '''
        self.sess.collections.remove(self.coll_path_a, force=True)
        self.sess.collections.remove(self.coll_path_b, force=True)
        self.sess.cleanup()

    def test_select(self):
        query = "SELECT COLL_NAME WHERE COLL_NAME = '{}'".format(self.coll_path_a)
        q = self.sess.genquery2_object()
        query_result = q.execute(query)
        self.assertIn([self.coll_path_a], query_result)
        self.assertEqual(len(query_result), 1)
        # Use upper() here in case GenQuery2 returns lowercase table names in a future implementation.
        self.assertIn('R_COLL_MAIN', q.get_sql(query).upper())

    def test_select_with_explicit_zone(self):
        query = "SELECT COLL_NAME WHERE COLL_NAME = '{}'".format(self.coll_path_a)
        q = self.sess.genquery2_object()
        query_result = q.execute(query, zone=self.sess.zone)
        self.assertIn([self.coll_path_a], query_result)
        self.assertEqual(len(query_result), 1)
        # Use upper() here in case GenQuery2 returns lowercase table names in a future implementation.
        self.assertIn('R_COLL_MAIN', q.get_sql(query).upper())

    def test_select_with_shorthand(self):
        query = "SELECT COLL_NAME WHERE COLL_NAME = '{}'".format(self.coll_path_a)
        query_result = self.sess.genquery2(query)
        self.assertIn([self.coll_path_a], query_result)
        self.assertEqual(len(query_result), 1)

    def test_select_with_shorthand_and_explicit_zone(self):
        query = "SELECT COLL_NAME WHERE COLL_NAME = '{}'".format(self.coll_path_a)
        query_result = self.sess.genquery2(query, zone=self.sess.zone)
        self.assertIn([self.coll_path_a], query_result)
        self.assertEqual(len(query_result), 1)

    def test_select_or(self):
        query = "SELECT COLL_NAME WHERE COLL_NAME = '{}' OR COLL_NAME = '{}'".format(self.coll_path_a, self.coll_path_b)
        q = self.sess.genquery2_object()
        query_result = q.execute(query)
        self.assertIn([self.coll_path_a], query_result)
        self.assertIn([self.coll_path_b], query_result)
        self.assertEqual(len(query_result), 2)
        # Use upper() here in case GenQuery2 returns lowercase table names in a future implementation.
        self.assertIn('R_COLL_MAIN', q.get_sql(query).upper())

    def test_select_and(self):
        query = "SELECT COLL_NAME WHERE COLL_NAME LIKE '{}' AND COLL_NAME LIKE '{}'".format(
            "%test_query2_coll%", "%query2_coll_a%")
        q = self.sess.genquery2_object()
        query_result = q.execute(query)
        self.assertIn([self.coll_path_a], query_result)
        self.assertEqual(len(query_result), 1)
        # Use upper() here in case GenQuery2 returns lowercase table names in a future implementation.
        self.assertIn('R_COLL_MAIN', q.get_sql(query).upper())

    def test_column_mappings(self):
        q = self.sess.genquery2_object()
        result = q.get_column_mappings()
        self.assertIn("COLL_ID", result.keys())
        self.assertIn("DATA_ID", result.keys())
        self.assertIn("RESC_ID", result.keys())
        self.assertIn("USER_ID", result.keys())
