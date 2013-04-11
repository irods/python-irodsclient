#!/usr/bin/env python
import unittest
from irods.session import iRODSSession

sess = iRODSSession(host='localhost', port=1247, user='rods', password='rods', 
    zone='tempZone')

class TestMessages(unittest.TestCase):
    
    def test_get_collection(self):
        path = "/tempZone/home/rods"
        coll = sess.get_collection(path)
        self.assertEquals(path, coll.path)


if __name__ == "__main__":
    unittest.main()
