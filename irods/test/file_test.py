#! /usr/bin/env python
import unittest
import os
import sys


class TestFiles(unittest.TestCase):
    """
    """
    test_coll_path = '/tempZone/home/rods/test_dir'
    test_obj_name = 'test1'
    test_content_str = 'blah'
    
    test_obj_path = test_coll_path + '/' + test_obj_name

    def setUp(self):
        from irods.session import iRODSSession
        import config

        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,  # 4444: why?
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)
        
        # Create test collection
        self.test_coll = self.sess.collections.create(self.test_coll_path)
        
        # Create test object and write to it
        self.test_obj = self.sess.data_objects.create(self.test_obj_path)
        with self.test_obj.open('r+') as f:
            f.write(self.test_content_str)

        
    def tearDown(self):
        '''Remove test data and close connections
        '''
        self.test_coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def test_file_open(self):
        #from irods.models import Collection, User, DataObject

        obj = self.sess.data_objects.get(self.test_obj_path)
        f = obj.open('r+')
        f.seek(0, 0)  # what does this return?
        str1 = f.read()
        #self.assertTrue(expr, msg)
        f.close()

    def test_file_read(self):
        #from irods.models import Collection, User, DataObject

        obj = self.sess.data_objects.get(self.test_obj_path)
        f = obj.open('r+')
        str1 = f.read(1024)
        #self.assertTrue(expr, msg)
        f.close()

    def test_file_write(self):
        #from irods.models import Collection, User, DataObject

        obj = self.sess.data_objects.get(self.test_obj_path)
        f = obj.open('w+')
        f.write("NEW STRING.py")
        f.seek(-6, 2)
        f.write("INTERRUPT")
        #self.assertTrue(expr, msg)
        f.close()


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()









