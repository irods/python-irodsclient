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

# Negating individual columns will exclude them from the row results.  Order is important.

for row in Query(
    conn, 
    (    DataObject,
         Collection,
         -DataObject.map_id,
         -DataObject.status,
         -Collection.map_id,
    )
).filter( Like(DataObject.name, 'a%'), ):
    coll = row[Collection.name]
    data = row[DataObject.name]
    print( f'{row[DataObject.id]=} {row[Collection.id]=}: {coll}/{data}')
