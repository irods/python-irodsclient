#! /usr/bin/env python2.6
import os
import sys
if __name__ == '__main__':
    sys.path.insert(0, os.path.abspath('../..'))

from irods.session import iRODSSession

sess = iRODSSession(host='localhost', port=4444, \
                    user='rods', password='rods', zone='tempZone')
coll = sess.get_collection('/tempZone/home/rods')
