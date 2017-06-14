Python iRODS Client (PRC)
=========================

[iRODS](https://www.irods.org) is an open-source distributed data management system. This is a client API implemented in python.

Currently supported:

- Establish a connection to iRODS, authenticate
- Implement basic Gen Queries (select columns and filtering)
- Support more advanced Gen Queries with limits, offsets, and aggregations
- Query the collections and data objects within a collection
- Execute direct SQL queries
- Execute iRODS rules
- Support read, write, and seek operations for files
- Delete data objects
- Create collections
- Delete collections
- Rename data objects
- Rename collections
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
- Python 2.7, 3.4 or newer

Installing
----------
PRC requires Python 2.7 or 3.4+.
To install with pip:
```bash
pip install python-irodsclient
```
or:
```bash
pip install git+https://github.com/irods/python-irodsclient.git[@branch|@commit|@tag]
```

Uninstalling
------------

```bash
pip uninstall python-irodsclient
```

Establishing a connection
-------------------------
```python
>>> from irods.session import iRODSSession
>>> sess = iRODSSession(host='localhost', port=1247, user='rods', password='rods', zone='tempZone')
```

If you're an administrator acting on behalf of another user:
```python
>>> from irods.session import iRODSSession
>>> sess = iRODSSession(host='localhost', port=1247, user='rods', password='rods', zone='tempZone', 
           client_user='another_user', client_zone='another_zone')
```

If no `client_zone` is provided, the `zone` parameter is used in its place.
    
Working with collections
------------------------
```python
>>> coll = sess.collections.get("/tempZone/home/rods")

>>> coll.id
45798

>>> coll.path
/tempZone/home/rods

>>> for col in coll.subcollections:
>>>   print col
<iRODSCollection /tempZone/home/rods/subcol1>
<iRODSCollection /tempZone/home/rods/subcol2>

>>> for obj in coll.data_objects:
>>>   print obj
<iRODSDataObject /tempZone/home/rods/file.txt>
<iRODSDataObject /tempZone/home/rods/file2.txt>
```

Create a new collection:
```python
>>> coll = sess.collections.create("/tempZone/home/rods/testdir")
>>> coll.id
45799
```
    
Working with data objects (files)
---------------------------------
Create a new data object:
```python
>>> obj = sess.data_objects.create("/tempZone/home/rods/test1")
<iRODSDataObject /tempZone/home/rods/test1>
```

Get an existing data object:
```python
>>> obj = sess.data_objects.get("/tempZone/home/rods/test1")
>>> obj.id
12345

>>> obj.name
test1
>>> obj.collection
<iRODSCollection /tempZone/home/rods>

>>> for replica in obj.replicas:
...     print replica.resource_name
...     print replica.number
...     print replica.path
...     print replica.status
...
demoResc
0
/var/lib/irods/Vault/home/rods/test1
1
```

Reading and writing files
-------------------------
PRC provides [file-like objects](http://docs.python.org/2/library/stdtypes.html#file-objects) for reading and writing files
```python
>>> obj = sess.data_objects.get("/tempZone/home/rods/test1")
>>> with obj.open('r+') as f:
...   f.write('foo\nbar\n')
...   f.seek(0,0)
...   for line in f:
...      print line
...
foo
bar
```
    
Working with metadata
---------------------
```python
>>> obj = sess.data_objects.get("/tempZone/home/rods/test1")
>>> print obj.metadata.items()
[]

>>> obj.metadata.add('key1', 'value1', 'units1')
>>> obj.metadata.add('key1', 'value2')
>>> obj.metadata.add('key2', 'value3')
>>> print obj.metadata.items()
[<iRODSMeta (key1, value1, units1, 10014)>, <iRODSMeta (key2, value3, None, 10017)>, 
<iRODSMeta (key1, value2, None, 10020)>]

>>> print obj.metadata.get_all('key1')
[<iRODSMeta (key1, value1, units1, 10014)>, <iRODSMeta (key1, value2, None, 10020)>]

>>> print obj.metadata.get_one('key2')
<iRODSMeta (key2, value3, None, 10017)>

>>> obj.metadata.remove('key1', 'value1', 'units1')
>>> print obj.metadata.items()
[<iRODSMeta (key2, value3, None, 10017)>, <iRODSMeta (key1, value2, None, 10020)>]
```

Performing general queries
--------------------------
```python
>>> from irods.session import iRODSSession
>>> from irods.models import Collection, User, DataObject
>>> sess = iRODSSession(host='localhost', port=1247, user='rods', password='rods', zone='tempZone')
>>> results = sess.query(DataObject.id, DataObject.name, DataObject.size, \
User.id, User.name, Collection.name).all()
>>> print results
+---------+-----------+-----------+---------------+--------------------------------+-----------+
| USER_ID | USER_NAME | D_DATA_ID | DATA_NAME     | COLL_NAME                      | DATA_SIZE |
+---------+-----------+-----------+---------------+--------------------------------+-----------+
| 10007   | rods      | 10012     | runDoxygen.rb | /tempZone/home/rods            | 5890      |
| 10007   | rods      | 10146     | test1         | /tempZone/home/rods            | 0         |
| 10007   | rods      | 10147     | test2         | /tempZone/home/rods            | 0         |
| 10007   | rods      | 10148     | test3         | /tempZone/home/rods            | 8         |
| 10007   | rods      | 10153     | test5         | /tempZone/home/rods            | 0         |
| 10007   | rods      | 10154     | test6         | /tempZone/home/rods            | 8         |
| 10007   | rods      | 10049     | .gitignore    | /tempZone/home/rods/pycommands | 12        |
| 10007   | rods      | 10054     | README.md     | /tempZone/home/rods/pycommands | 3795      |
| 10007   | rods      | 10052     | coll_test.py  | /tempZone/home/rods/pycommands | 658       |
| 10007   | rods      | 10014     | file_test.py  | /tempZone/home/rods/pycommands | 465       |
+---------+-----------+-----------+---------------+--------------------------------+-----------+
```

Query with aggregation(min, max, sum, avg, count):
```python
>>> results = sess.query(DataObject.owner_name).count(DataObject.id).sum(DataObject.size).all()
>>> print results
+--------------+-----------+-----------+
| D_OWNER_NAME | D_DATA_ID | DATA_SIZE |
+--------------+-----------+-----------+
| rods         | 10        | 10836     |
+--------------+-----------+-----------+
```

Run a Specifc Query (similar to iquest --sql <name>), using the 0.6.0 additional functionality of reading the iRODS environment files:
--------------------------------------------------------------------------------------------------------------------------------------
```python
>>> import os
>>> import json
>>> 
>>> from irods.session import iRODSSession
>>> from irods.models import Collection, DataObject, Resource
>>> from irods.query import SpecificQuery
>>> 
>>> 
>>> def get_session():
...     """
...     establish a session to the iCAT server, using the iRODS environment env_file
...     (MUST use library version >= 0.6.0)
...     evaluate where to get the session information from,
...     return an iRODS session *and* array with irods_environment.json info encoded for later use
...     example decoded irods_environment.json;
...         >>> pprint(ienv)
...         {u'irods_authentication_scheme': u'KRB',
...          u'irods_cwd': u'/DevZone/home/john',
...          u'irods_def_resource': u'wtsiusers',
...          u'irods_home': u'/DevZone/home/john',
...          u'irods_host': u'icat.genomeresearch.ac.uk',
...          u'irods_port': 1247,
...          u'irods_user_name': u'john',
...          u'irods_zone_name': u'DevZone'}
...     """
...     try:
...         env_file = os.environ['IRODS_ENVIRONMENT_FILE']
...     except KeyError:
...         env_file = os.path.expanduser('~/.irods/irods_environment.json')
...     with open(env_file) as data_file:
...         ienv = json.load(data_file)
...     return (iRODSSession(irods_env_file=env_file), ienv)
... 
>>> 
>>> 
>>> (SESS, ienv_info) = get_session()
>>> 
>>> #test session working OK
... col_to_check = "/{}/home/irods".format(ienv_info['irods_zone_name'])
>>> coll = SESS.collections.get(col_to_check)
>>> print coll.id
10286
>>> 
>>> CompoundResourceTree = "root"
>>> # make specific query
... sql = "select count(*) from r_data_main where resc_name = '{}' and data_is_dirty = '0'".format(CompoundResourceTree)
>>> sql_alias = 'DirtyReplicas{}'.format(CompoundResourceTree)
>>> query = SpecificQuery(SESS, sql, sql_alias)
>>> 
>>> # register query in iCAT
... query.register()
<irods.message.iRODSMessage object at 0x1face50>
>>> 
>>> #run the Specific Query
... res_q = SpecificQuery(SESS, alias=sql_alias)
>>> res_q.get_results()
<generator object get_results at 0x1d2e730>
>>> for r in res_q.get_results():
...     print(r[0])
... 
0

```
