#! /usr/bin/env python
from irods.session import iRODSSession
from irods.models import Collection, User, DataObject
import logging

sess = iRODSSession(host='localhost', port=1247, \
	user='rods', password='rods', zone='tempZone')

obj = sess.get_data_object("/tempZone/home/rods/test1")
f = obj.open('r')
