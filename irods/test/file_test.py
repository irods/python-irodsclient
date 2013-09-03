#! /usr/bin/env python
import os
import sys
if __name__ == '__main__':
    sys.path.insert(0, os.path.abspath('../..'))

from irods.session import iRODSSession
from irods.models import Collection, User, DataObject
import logging

sess = iRODSSession(host='localhost', port=1247, \
                                          user='rods', password='rods', zone='tempZone')

obj = sess.get_data_object("/tempZone/home/rods/test1")
f = obj.open('w+')
str = f.read(1024)
logging.debug(str)

f.write("NEW STRING.py")
f.seek(-6, 2)
f.write("INTERRUPT")

f.seek(0, 0)
str = f.read()
logging.debug(str)

f.close()
