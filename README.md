pycommands
============

[iRODS](https://www.irods.org) is an open-source distributed filesystem manager.  This a client API implemented in python.

This project should be considered pre-alpha. Here's what works:
- [x] Establish a connection to iRODS, authenticaate
- [x] Implement basic Gen Queries (select columns and filtering)
- [ ] Support more advanced Gen Queries with limits, offsets, and aggregations
- [x] Query the collections and data objects within a collection
- [x] Support read, write, and seek operations for files
- [x] Delete data objects
- [ ] Rename data objects
- [ ] Create collections
- [ ] Delete collections
- [ ] Rename collections
- [X] Query metadata for collections and data objects
- [X] Add, edit, remove metadata
- [ ] Replicate data objects to different resource servers
- [ ] Connection pool management
- [ ] Implement gen query result sets as lazy queries
- [X] Return empty result sets when CAT_NO_ROWS_FOUND is raised
- [ ] Optimize querying subcollections and data_objects by maintaining a cache 
and checking last modified timestamps

Installation
------------
    pip install git+git://github.com/cjlarose/pycommands.git

Establishing a connection
-------------------------
```python
>>> from irods.session import iRODSSession
>>> sess = iRODSSession(host='localhost', port=1247, user='rods', password='rods', zone='tempZone')
```
    
Working with collections
------------------------
```python
>>> coll = sess.collections.get_collection("/tempZone/home/rods")

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
    
Working with data objects (files)
---------------------------------
Create a new data object:
```python
>>> obj = sess.data_objects.create_data_object("/tempZone/home/rods/test1")
<iRODSDataObject /tempZone/home/rods/test1>
```

Get an existing data object:
```python
>>> obj = sess.data_objects.get_data_object("/tempZone/home/rods/test1")
>>> obj.id
12345

>>> obj.name
test1
>>> obj.collection
<iRODSCollection /tempZone/home/rods>
```

Reading and writing files
-----------------------
pycommands provides [file-like objects](http://docs.python.org/2/library/stdtypes.html#file-objects) for reading and writiing files
```python
>>> obj = sess.data_objects.get_data_object("/tempZone/home/rods/test1")
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
>>> from irods.meta import iRODSMeta
>>> obj = sess.data_objects.get_data_object("/tempZone/home/rods/test1")
>>> print obj.metadata.items()
[]

>>> obj.metadata.add(iRODSMeta('key1', 'value1', 'units1'))
>>> obj.metadata.add(iRODSMeta('key1', 'value2'))
>>> obj.metadata.add(iRODSMeta('key2', 'value3'))
>>> print obj.metadata.items()
[<iRODSMeta (key1, value1, units1, 10014)>, <iRODSMeta (key2, value3, None, 10017)>, 
<iRODSMeta (key1, value2, None, 10020)>]

>>> print obj.metadata.get_all('key1')
[<iRODSMeta (key1, value1, units1, 10014)>, <iRODSMeta (key1, value2, None, 10020)>]

>>> print obj.metadata.get_one('key2')
<iRODSMeta (key2, value3, None, 10017)>

>>> obj.metadata.remove(iRODSMeta('key1', 'value1', 'units1'))
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
```
