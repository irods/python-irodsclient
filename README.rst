=========================
Python iRODS Client (PRC)
=========================

`iRODS <https://www.irods.org>`_ is an open source distributed data management system. This is a client API implemented in python.

Currently supported:

- Establish a connection to iRODS, authenticate
- Implement basic Gen Queries (select columns and filtering)
- Support more advanced Gen Queries with limits, offsets, and aggregations
- Query the collections and data objects within a collection
- Execute direct SQL queries
- Execute iRODS rules
- Support read, write, and seek operations for files
- PUT/GET data objects
- Create data objects
- Delete data objects
- Create collections
- Delete collections
- Rename data objects
- Rename collections
- Register files and directories
- Query metadata for collections and data objects
- Add, edit, remove metadata
- Replicate data objects to different resource servers
- Connection pool management
- Implement gen query result sets as lazy queries
- Return empty result sets when CAT_NO_ROWS_FOUND is raised
- Manage permissions
- Manage users and groups
- Manage resources
- GSI authentication
- Unicode strings
- Ticket based access
- iRODS connection over SSL
- Python 2.7, 3.4 or newer


Installing
----------

PRC requires Python 2.7 or 3.4+.
To install with pip::

 pip install python-irodsclient

or::

 pip install git+https://github.com/irods/python-irodsclient.git[@branch|@commit|@tag]


Uninstalling
------------

::

 pip uninstall python-irodsclient


Establishing a connection
-------------------------

Using environment files in ``~/.irods/``:

>>> import os
>>> from irods.session import iRODSSession
>>> try:
...     env_file = os.environ['IRODS_ENVIRONMENT_FILE']
... except KeyError:
...     env_file = os.path.expanduser('~/.irods/irods_environment.json')
...
>>> with iRODSSession(irods_env_file=env_file) as session:
...     pass
...
>>>

Passing iRODS credentials as keyword arguments:

>>> from irods.session import iRODSSession
>>> with iRODSSession(host='localhost', port=1247, user='bob', password='1234', zone='tempZone') as session:
...     pass
...
>>>

If you're an administrator acting on behalf of another user:

>>> from irods.session import iRODSSession
>>> with iRODSSession(host='localhost', port=1247, user='rods', password='1234', zone='tempZone',
           client_user='bob', client_zone='possibly_another_zone') as session:
...     pass
...
>>>

If no ``client_zone`` is provided, the ``zone`` parameter is used in its place.


Working with collections
------------------------

>>> coll = session.collections.get("/tempZone/home/rods")

>>> coll.id
45798

>>> coll.path
/tempZone/home/rods

>>> for col in coll.subcollections:
>>>   print(col)
<iRODSCollection /tempZone/home/rods/subcol1>
<iRODSCollection /tempZone/home/rods/subcol2>

>>> for obj in coll.data_objects:
>>>   print(obj)
<iRODSDataObject /tempZone/home/rods/file.txt>
<iRODSDataObject /tempZone/home/rods/file2.txt>


Create a new collection:

>>> coll = session.collections.create("/tempZone/home/rods/testdir")
>>> coll.id
45799


Working with data objects (files)
---------------------------------

Create a new data object:

>>> obj = session.data_objects.create("/tempZone/home/rods/test1")
<iRODSDataObject /tempZone/home/rods/test1>

Get an existing data object:

>>> obj = session.data_objects.get("/tempZone/home/rods/test1")
>>> obj.id
12345

>>> obj.name
test1
>>> obj.collection
<iRODSCollection /tempZone/home/rods>

>>> for replica in obj.replicas:
...     print(replica.resource_name)
...     print(replica.number)
...     print(replica.path)
...     print(replica.status)
...
demoResc
0
/var/lib/irods/Vault/home/rods/test1
1


Using the put() method rather than the create() method will trigger different policy enforcement points (PEPs) on the server.

Put an existing file as a new data object:

>>> session.data_objects.put("test.txt","/tempZone/home/rods/test2")
>>> obj2 = session.data_objects.get("/tempZone/home/rods/test2")
>>> obj2.id
56789


Reading and writing files
-------------------------

PRC provides `file-like objects <http://docs.python.org/2/library/stdtypes.html#file-objects) for reading and writing files>`_

>>> obj = session.data_objects.get("/tempZone/home/rods/test1")
>>> with obj.open('r+') as f:
...   f.write('foo\nbar\n')
...   f.seek(0,0)
...   for line in f:
...      print(line)
...
foo
bar


Working with metadata
---------------------

>>> obj = session.data_objects.get("/tempZone/home/rods/test1")
>>> print(obj.metadata.items())
[]

>>> obj.metadata.add('key1', 'value1', 'units1')
>>> obj.metadata.add('key1', 'value2')
>>> obj.metadata.add('key2', 'value3')
>>> print(obj.metadata.items())
[<iRODSMeta (key1, value1, units1, 10014)>, <iRODSMeta (key2, value3, None, 10017)>,
<iRODSMeta (key1, value2, None, 10020)>]

>>> print(obj.metadata.get_all('key1'))
[<iRODSMeta (key1, value1, units1, 10014)>, <iRODSMeta (key1, value2, None, 10020)>]

>>> print(obj.metadata.get_one('key2'))
<iRODSMeta (key2, value3, None, 10017)>

>>> obj.metadata.remove('key1', 'value1', 'units1')
>>> print(obj.metadata.items())
[<iRODSMeta (key2, value3, None, 10017)>, <iRODSMeta (key1, value2, None, 10020)>]


General queries
---------------

>>> import os
>>> from irods.session import iRODSSession
>>> from irods.models import Collection, DataObject
>>>
>>> env_file = os.path.expanduser('~/.irods/irods_environment.json')
>>> with iRODSSession(irods_env_file=env_file) as session:
...     query = session.query(Collection.name, DataObject.id, DataObject.name, DataObject.size)
...
...     for result in query:
...             print('{}/{} id={} size={}'.format(result[Collection.name], result[DataObject.name], result[DataObject.id], result[DataObject.size]))
...
/tempZone/home/rods/manager/access_manager.py id=212665 size=2164
/tempZone/home/rods/manager/access_manager.pyc id=212668 size=2554
/tempZone/home/rods/manager/collection_manager.py id=212663 size=4472
/tempZone/home/rods/manager/collection_manager.pyc id=212664 size=4464
/tempZone/home/rods/manager/data_object_manager.py id=212662 size=10291
/tempZone/home/rods/manager/data_object_manager.pyc id=212667 size=8772
/tempZone/home/rods/manager/__init__.py id=212670 size=79
/tempZone/home/rods/manager/__init__.pyc id=212671 size=443
/tempZone/home/rods/manager/metadata_manager.py id=212660 size=4263
/tempZone/home/rods/manager/metadata_manager.pyc id=212659 size=4119
/tempZone/home/rods/manager/resource_manager.py id=212666 size=5329
/tempZone/home/rods/manager/resource_manager.pyc id=212661 size=4570
/tempZone/home/rods/manager/user_manager.py id=212669 size=5509
/tempZone/home/rods/manager/user_manager.pyc id=212658 size=5233

Query with aggregation(min, max, sum, avg, count):

>>> with iRODSSession(irods_env_file=env_file) as session:
...     query = session.query(DataObject.owner_name).count(DataObject.id).sum(DataObject.size)
...     print(next(query.get_results()))
{<irods.column.Column 411 D_OWNER_NAME>: 'rods', <irods.column.Column 407 DATA_SIZE>: 62262, <irods.column.Column 401 D_DATA_ID>: 14}

In this case since we are expecting only one row we can directly call ``query.execute()``:

>>> with iRODSSession(irods_env_file=env_file) as session:
...     query = session.query(DataObject.owner_name).count(DataObject.id).sum(DataObject.size)
...     print(query.execute())
+--------------+-----------+-----------+
| D_OWNER_NAME | D_DATA_ID | DATA_SIZE |
+--------------+-----------+-----------+
| rods         | 14        | 62262     |
+--------------+-----------+-----------+


Specific Queries
----------------

>>> import os
>>> from irods.session import iRODSSession
>>> from irods.models import Collection, DataObject
>>> from irods.query import SpecificQuery
>>>
>>> env_file = os.path.expanduser('~/.irods/irods_environment.json')
>>> with iRODSSession(irods_env_file=env_file) as session:
...     # define our query
...     sql = "select data_name, data_id from r_data_main join r_coll_main using (coll_id) where coll_name = '/tempZone/home/rods/manager'"
...     alias = 'list_data_name_id'
...     columns = [DataObject.name, DataObject.id] # optional, if we want to get results by key
...     query = SpecificQuery(session, sql, alias, columns)
...
...     # register specific query in iCAT
...     _ = query.register()
...
...     for result in query:
...             print('{} {}'.format(result[DataObject.name], result[DataObject.id]))
...
...     # delete specific query
...     _ = query.remove()
...
user_manager.pyc 212658
metadata_manager.pyc 212659
metadata_manager.py 212660
resource_manager.pyc 212661
data_object_manager.py 212662
collection_manager.py 212663
collection_manager.pyc 212664
access_manager.py 212665
resource_manager.py 212666
data_object_manager.pyc 212667
access_manager.pyc 212668
user_manager.py 212669
__init__.py 212670
__init__.pyc 212671

Recherché queries
-----------------

In some cases you might like to use a GenQuery operator not directly offered by this
Python library, or even combine query filters in ways GenQuery may not directly support.

As an example, the code below finds metadata value fields lexicographically outside the range
of decimal integers, while also requiring that the data objects to which they are attached do
not reside in the trash.

>>> search_tuple = (DataObject.name , Collection.name ,
...                 DataObjectMeta.name , DataObjectMeta.value)

>>> # "not like" : direct instantiation of Criterion (operator in literal string)
>>> not_in_trash = Criterion ('not like', Collection.name , '%/trash/%')

>>> # "not between"( column, X, Y) := column < X OR column > Y ("OR" done via chained iterators)
>>> res1 = session.query (* search_tuple).filter(not_in_trash).filter(DataObjectMeta.value < '0')
>>> res2 = session.query (* search_tuple).filter(not_in_trash).filter(DataObjectMeta.value > '9' * 9999 )

>>> chained_results = itertools.chain ( res1.get_results(), res2.get_results() )
>>> pprint( list( chained_results ) )


And more...
-----------

Additional code samples are available in the `test directory <https://github.com/irods/python-irodsclient/tree/master/irods/test>`_
