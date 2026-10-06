#!/usr/bin/env python3
from irods.client.connection import Connection
from irods.client.account import iRODSAccount

account = iRODSAccount(
    'localhost',
    1247,
    'rods',
    'tempZone',
    password='rods')
conn = Connection(account, authenticate=False)
print(conn.server_version)
