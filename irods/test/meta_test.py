#! /usr/bin/env python
import unittest
import os
import sys
from irods.models import (DataObject, Collection, Resource, User, DataObjectMeta, 
    CollectionMeta, ResourceMeta, UserMeta)


class TestMeta(unittest.TestCase):
    """
    """

    def setUp(self):
        from irods.session import iRODSSession
        import config

        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)
        
    def tearDown(self):
        '''Remove test data and close connections
        '''
        #self.test_coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def test_get_meta(self):
        """
        """
        #from irods.meta import iRODSMeta

        #obj = self.sess.get_data_object("/tempZone/home/rods/test1")
        meta = self.sess.metadata.get(DataObject, '/tempZone/home/rods/test1')
        print meta
        #self.assertEqual(first, second, msg)

    @unittest.skip('')
    def test_add_meta(self):
        """
        """
        from irods.meta import iRODSMeta

        self.sess.add_meta('d', '/tempZone/home/rods/test1',
                           iRODSMeta('key8', 'value5'))

    @unittest.skip('')
    def test_copy_meta(self):
        """
        """
        #from irods.meta import iRODSMeta
        self.sess.copy_meta('d', 'd', '/tempZone/home/rods/test1',
                            '/tempZone/home/rods/test2')

    @unittest.skip('')
    def test_remove_meta(self):
        """
        """
        from irods.meta import iRODSMeta

        self.sess.remove_meta('d', '/tempZone/home/rods/test1',
                              iRODSMeta('key8', 'value5'))


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
