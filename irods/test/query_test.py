#! /usr/bin/env python2.6
import unittest
import os
import sys
from irods.models import User, Collection, Keywords, DataObject
from irods.session import iRODSSession
import config


class TestQuery(unittest.TestCase):
    """
    """
    # test data
    coll_path = '/{0}/home/{1}/test_dir'.format(config.IRODS_SERVER_ZONE, config.IRODS_USER_USERNAME)
    obj_name = 'test1'
    obj_path = '{0}/{1}'.format(coll_path, obj_name)
    

    def setUp(self):
        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,  # 4444 why?
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
        

    def test_collections_query(self):
        # collection query test
        result = self.sess.query(Collection.id, Collection.name).all()
        assert ( result.has_value(self.coll_path) )

#         q1 = self.sess.query(User, Collection.name)
#         q2 = q1.filter(User.name == 'cjlarose')
#         q3 = q2.filter(Keywords.chksum == '12345')
#    
#         f = open('select', 'w')
#         f.write(q1._select_message().pack())
#           
#         f = open('conds', 'w')
#         f.write(q1._conds_message().pack())
#           
#         f = open('condskw', 'w')
#         f.write(q1._kw_message().pack())
#           
#         f = open('genq', 'w')
#         f.write(q1._message().pack())

        #print result

        """
        cut-n-pasted from collection_test...
        """

        #q1 = sess.query(Collection.id).filter(Collection.name == "'/tempZone/home/rods'")
        #q1.all()

        #f = open('collquery', 'w')
        #f.write(q1._message().pack())

        #result = sess.query(Collection.id, Collection.owner_name, User.id, User.name)\
        #    .filter(Collection.owner_name == "'rods'")\
        #    .all()
        
        #print result
        
        
        
    def test_files_query(self):
        # file query test
        result = self.sess.query(DataObject.id, DataObject.collection_id, DataObject.name, User.name, Collection.name).all()
        assert ( result.has_value(self.obj_name) )



if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
