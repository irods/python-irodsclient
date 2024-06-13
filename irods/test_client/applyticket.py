#!/usr/bin/env python
import sys,os
import irods.test.helpers as h
from irods.simple_client import Session
from irods.ticket import Ticket
#s = h.make_session()

ENV_FILE = irods_env_file=os.path.expanduser('~/.irods/irods_environment.json')
s = Session(irods_env_file = ENV_FILE)

if len(sys.argv) > 1:
    Ticket(s,sys.argv[1]).supply()
from irods.models import DataObject,Collection
q = s.query( DataObject.name,Collection.name)

print('data objects:')
print('-------------')
for d in list(q):
    print( d[Collection.name],'/',
        d[DataObject.name],sep='')
