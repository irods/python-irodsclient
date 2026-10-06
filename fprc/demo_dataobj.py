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

from irods.client.data import (
  data_open,
  data_write,
  data_read,
  data_close,
  data_seek,
  O_RDWR,
  O_CREAT,
)

desc = data_open(conn, '/tempZone/home/rods/abc.dat', O_RDWR|O_CREAT)
data_write(conn, desc, b'hello world')
data_seek(conn, desc, 1)
print( "Read from data object:",
  data_read(conn, desc, 100).decode()
)
data_close(conn, desc)
