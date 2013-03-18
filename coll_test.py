#! /usr/bin/env python
from irods.session import iRODSSession
from irods.models import Collection, User, DataObject
import logging

sess = iRODSSession(host='localhost', port=1247, \
	user='rods', password='rods', zone='tempZone')
#q1 = sess.query(Collection.id).filter(Collection.name == "'/tempZone/home/rods'")
#q1.all()

#f = open('collquery', 'w')
#f.write(q1._message().pack())

#result = sess.query(Collection.id, Collection.owner_name, User.id, User.name)\
#    .filter(Collection.owner_name == "'rods'")\
#    .all()

result = sess.query(DataObject.id, DataObject.collection_id, DataObject.name, DataObject.replica_number, DataObject.version, DataObject.type, DataObject.size, User.id, User.name, Collection.id, Collection.name).all()

print str(result)
