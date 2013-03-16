#! /usr/bin/env python2.6
from irods.session import iRODSSession
from irods.models import Collection
import logging

sess = iRODSSession(host='localhost', port=4444, \
	user='rods', password='rods', zone='tempZone')
q1 = sess.query(Collection.id).filter(Collection.name == "'/tempZone/home/rods'")
#q1.all()

f = open('collquery', 'w')
f.write(q1._message().pack())

q1.all()
