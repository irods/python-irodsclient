Python iRODS Client (PRC)
============

[iRODS](https://www.irods.org) is an open-source distributed filesystem manager.  This a client API implemented in python.

This project should be considered pre-alpha. Here's what works:
- [x] Establish a connection to iRODS, authenticate
- [x] Implement basic Gen Queries (select columns and filtering)
- [ ] Support more advanced Gen Queries with limits, offsets, and aggregations
- [x] Query the collections and data objects within a collection
- [x] Support read, write, and seek operations for files
- [x] Delete data objects
- [x] Create collections
- [x] Delete collections
- [x] Rename data objects
- [x] Rename collections
- [x] Query metadata for collections and data objects
- [x] Add, edit, remove metadata
- [ ] Replicate data objects to different resource servers
- [x] Connection pool management
- [x] Implement gen query result sets as lazy queries
- [x] Return empty result sets when CAT_NO_ROWS_FOUND is raised
- [x] Manage permissions
- [x] Manage users and groups
- [ ] Manage zones
- [x] Manage resources

Installation
------------
PRC requires Python 2.7. Installation with pip is easy!

    pip install git+git://github.com/irods/python-irodsclient.git

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
```

Reading and writing files
-----------------------
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
