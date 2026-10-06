from os.path import abspath, dirname, join
import sys
import uuid

from irods.client.data import (
    data_open,
    data_close,
    data_unlink,
    O_CREAT,
    O_WRONLY
)
from irods.client.connection import Connection
from irods.client.metadata import avu_operation, irods_object_type
from irods.client.account import iRODSAccount
from irods.client.query import Query
from irods.client.query.models import DataObjectMeta, DataObject

def pseudorandom_string():
    return uuid.uuid1().hex


account = iRODSAccount(
    'localhost',
    1247,
    user := 'rods',
    zone := 'tempZone',
    password='rods'
)

PATH = f'/{zone}/home/{user}/abc.dat-' + pseudorandom_string()

conn = Connection( account )

def test_data_and_metadata_create():
    desc = None
    try:
        # Create a data object.
        desc = data_open(conn, PATH, O_WRONLY|O_CREAT)
        data_close(conn, desc)

        my_avu = (pseudorandom_string(), 'my-value', 'my-units')

        def my_avu_occurrences():
            "For tests, return the number of avu's both attached to a data object and matching the name field for my_avu"
            return len(list(Query(conn, (DataObjectMeta, DataObject)).filter(DataObjectMeta.name == my_avu[0])))

        # Attach an AVU, then delete it.  For both operations, check that a query gives the expected number of result rows.
        avu_operation(conn, irods_object_type.DATA_OBJECT, "add", PATH, my_avu)
        assert(my_avu_occurrences() == 1)

        avu_operation(conn, irods_object_type.DATA_OBJECT, "rm", PATH, my_avu)
        assert(my_avu_occurrences() == 0)

    finally:
        if desc is not None:
            data_unlink(conn, PATH, force=True)
