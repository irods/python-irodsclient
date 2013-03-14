#! /usr/bin/env python2.6
from irods.session import iRODSSession

sess = iRODSSession(host='localhost', port=4444, \
	user='rods', password='rods', zone='tempZone')
sess._login()
sess.disconnect()
