#! /usr/bin/env python
import os
import sys
if (sys.version_info >= (2, 7)):
    import unittest
else:
    import unittest2 as unittest
from irods.models import Collection, DataObject
from irods.session import iRODSSession
import config


def make_dummy_object(session, path):
    content = 'blah'
        
    obj = session.data_objects.create(path)
    with obj.open('w') as f:
        f.write(content)
        
    return obj

        
def make_dummy_collection(session, path, obj_count):
    coll = session.collections.create(path)
    
    for n in range(obj_count):
        obj_path = path + "/dummy" + str(n).zfill(6) + ".txt"
        make_dummy_object(session, obj_path)
    
    return coll


class TestContinueQuery(unittest.TestCase):
    """
    """
    # test data
    coll_path = '/{0}/home/{1}/test_dir'.format(config.IRODS_SERVER_ZONE, config.IRODS_USER_USERNAME)
    obj_count = 2500


    def setUp(self):
        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)
        
        # Create dummy test collection
        self.coll = make_dummy_collection(self.sess, self.coll_path, self.obj_count)

        
    def tearDown(self):
        '''Remove test data and close connections
        '''
        self.coll.remove(recurse=True, force=True)
        self.sess.cleanup()


    def test_files_generator(self):
        # Query for all files in test collection
        query = self.sess.query(DataObject.name, Collection.name).filter(Collection.name == self.coll_path)
        
        counter = 0;
        
        for result in query.get_results():  
            # what we should see
            object_path = self.coll_path + "/dummy" + str(counter).zfill(6) + ".txt"
            
            # what we see
            result_path = "{0}/{1}".format(result[Collection.name], result[DataObject.name])
            
            # compare
            self.assertEqual(result_path, object_path)
            counter += 1;
        
        # make sure we got all of them
        self.assertEqual(counter, self.obj_count)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
