#! /usr/bin/env python
import os
import sys
if __name__ == '__main__':
    sys.path.insert(0, os.path.abspath('../..'))

import logging
from irods.session import iRODSSession
from irods.models import Collection, User, DataObject
from irods.meta import iRODSMeta

sess = iRODSSession(host='localhost', port=1247, \
                                          user='rods', password='rods', zone='tempZone')

obj = sess.get_data_object("/tempZone/home/rods/test1")

meta = sess.get_meta('d', "/tempZone/home/rods/test1")
print meta

sess.add_meta('d', '/tempZone/home/rods/test1', iRODSMeta('key8', 'value5'))
sess.remove_meta('d', '/tempZone/home/rods/test1', iRODSMeta('key8', 'value5'))

sess.copy_meta('d', 'd', '/tempZone/home/rods/test1', '/tempZone/home/rods/test2')

#meta = sess.get_meta('d', "/tempZone/home/rods/test1")
#print meta
