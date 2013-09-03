#!/usr/bin/env python
import os
import sys
if __name__ == '__main__':
    sys.path.insert(0, os.path.abspath('../..'))

import unittest
from irods.session import iRODSSession

sess = iRODSSession(host='localhost', port=1247, user='rods', password='rods',
    zone='tempZone')

class TestMessages(unittest.TestCase):

    def test_get_collection(self):
        path = "/tempZone/home/rods"
        coll = sess.get_collection(path)
        self.assertEquals(path, coll.path)

        new_coll = sess.create_collection("/tempZone/home/rods/test_dir")
        self.assertEquals(new_coll.name, 'test_dir')

if __name__ == "__main__":
    unittest.main()
