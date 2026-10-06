#!/usr/bin/env python3
from irods.client.connection import Connection
from irods.client.account import iRODSAccount
from irods.client.query import Query
from irods.client.query.models import DataObject,Collection
from irods.client.query.column import Like

account = iRODSAccount(
    'localhost',
    1247,
    'rods',
    'tempZone',
    password='rods'
)

conn = Connection( account )

for row in Query(conn, [DataObject, Collection.name]).filter(Like(DataObject.name, 'a%')):
  coll = row[Collection.name]
  id = row[DataObject.id]
  data = row[DataObject.name]
  print( f'{id}: {coll}/{data}')
