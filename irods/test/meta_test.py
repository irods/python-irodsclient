#! /usr/bin/env python
import unittest
import os
import sys
from irods.meta import iRODSMeta
from irods.models import (DataObject, Collection, Resource, User, DataObjectMeta, 
    CollectionMeta, ResourceMeta, UserMeta)
from irods.session import iRODSSession
import config




class TestMeta(unittest.TestCase):
    '''Suite of tests on metadata operations
    '''
    
    # test data
    coll_path = '/{0}/home/{1}/test_dir'.format(config.IRODS_SERVER_ZONE, config.IRODS_USER_USERNAME)
    obj_name = 'test1'
    obj_path = '{0}/{1}'.format(coll_path, obj_name)
    
    # test metadata
    (attr0, value0, unit0) = ('attr0', 'value0', 'unit0')
    (attr1, value1, unit1) = ('attr1', 'value1', 'unit1')
    

    def setUp(self):
        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)
        
        # Create test collection and (empty) test object
        self.coll = self.sess.collections.create(self.coll_path)
        self.obj = self.sess.data_objects.create(self.obj_path)

        
    def tearDown(self):
        '''Remove test data and close connections
        '''
        self.coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def test_get_obj_meta(self):
        """
        """
        # get object metadata
        meta = self.sess.metadata.get(DataObject, self.obj_path)
        
        # there should be no metadata at this point
        assert (len(meta) == 0)
        
        #self.assertEqual(first, second, msg)


    def test_add_obj_meta(self):
        """
        """

        # add metadata to test object
        self.sess.metadata.add(DataObject, self.obj_path,
                           iRODSMeta(self.attr0, self.value0))
        self.sess.metadata.add(DataObject, self.obj_path,
                           iRODSMeta(self.attr1, self.value1, self.unit1))
        
        # get object metadata
        meta = self.sess.metadata.get(DataObject, self.obj_path)
        
        # assertions
        assert(meta[0].name == self.attr0)
        assert(meta[0].value == self.value0)
        
        assert(meta[1].name == self.attr1)
        assert(meta[1].value == self.value1)
        assert(meta[1].units == self.unit1)


    def test_copy_obj_meta(self):
        """
        """
        
        # test destination object for copy
        dest_obj_path = self.coll_path + '/test2'
        self.sess.data_objects.create(dest_obj_path)
        
        # add metadata to test object
        self.sess.metadata.add(DataObject, self.obj_path,
                           iRODSMeta(self.attr0, self.value0))
        
        # copy metadata
        self.sess.metadata.copy(DataObject, DataObject, self.obj_path, dest_obj_path)
        
        # get destination object metadata
        dest_meta = self.sess.metadata.get(DataObject, dest_obj_path)
        
        # check metadata
        assert(dest_meta[0].name == self.attr0)        


    def test_remove_obj_meta(self):
        """
        """
        
        # add metadata to test object
        self.sess.metadata.add(DataObject, self.obj_path,
                           iRODSMeta(self.attr0, self.value0))
        
        # check that metadata is there
        meta = self.sess.metadata.get(DataObject, self.obj_path)
        assert(meta[0].name == self.attr0)

        # remove metadata from object
        self.sess.metadata.remove(DataObject, self.obj_path,
                              iRODSMeta(self.attr0, self.value0))
        
        # check that metadata is gone
        meta = self.sess.metadata.get(DataObject, self.obj_path)
        assert (len(meta) == 0)


    def test_add_coll_meta(self):
        """
        """

        # add metadata to test collection
        self.sess.metadata.add(Collection, self.coll_path,
                           iRODSMeta(self.attr0, self.value0))
        
        # get collection metadata
        meta = self.sess.metadata.get(Collection, self.coll_path)
        
        # assertions
        assert(meta[0].name == self.attr0)
        assert(meta[0].value == self.value0)
        
        # remove collection metadata
        self.sess.metadata.remove(Collection, self.coll_path,
                           iRODSMeta(self.attr0, self.value0))
        
        # check that metadata is gone
        meta = self.sess.metadata.get(Collection, self.coll_path)
        assert (len(meta) == 0)
        



if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
