python-irods
============

[iRODS](https://www.irods.org) is an open-source distributed filesystem manager.  This a client API implemented in python.

This project should be considered pre-alpha. Not a lot works yet, but it's coming along. The following are guidelines for using the API.  Most of it is unimplemented.

Establishing a connection
-------------------------
```python
>>> from irods.session import iRODSSession
>>> sess = iRODSSession(host='localhost', port=1247, user='rods', password='rods', zone='tempZone')
```
    
Working with collections
------------------------
```python
>>> coll = sess.get_collection("/tempZone/home/rods")

>>> coll.id
45798
>>> coll.name
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
>>> obj = sess.create_data_object("/tempZone/home/rods/test1")
<iRODSDataObject /tempZone/home/rods/test1>
```

Get an existing data object:
```python
>>> obj = sess.get_data_object("/tempZone/home/rods/test1")
>>> obj.id
12345
>>> obj.name
test1
>>> obj.collection
<iRODSCollection /tempZone/home/rods>
```

Reading a writing files
-----------------------
python-irods provides [file-like objects](http://docs.python.org/2/library/stdtypes.html#file-objects) for reading and writiing files
```python
>>> obj = sess.get_data_object("/tempZone/home/rods/test1")
>>> with obj.open('r+') as f:
...   f.write('foo\nbar')
...   f.seek(0,0)
...   print f.read(1024)
...
foo
bar
```
    
Working with metadata
---------------------

Performing general queries
--------------------------
```python
>>> from irods.session import iRODSSession
>>> from irods.models import Collection, User, DataObject
>>> sess = iRODSSession(host='localhost', port=1247, user='rods', password='rods', zone='tempZone')
>>> results = sess.query(DataObject.id, DataObject.collection_id, DataObject.name, \
DataObject.replica_number, DataObject.version, DataObject.type, DataObject.size, \
User.id, User.name, Collection.id, Collection.name).all()
```
