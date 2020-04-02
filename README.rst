=========================
Python iRODS Client (PRC)
=========================

`iRODS <https://www.irods.org>`_ is an open source distributed data management system. This is a client API implemented in Python.

Currently supported:

- Establish a connection to iRODS
- Authenticate via password, GSI, PAM
- iRODS connection over SSL
- Implement basic GenQueries (select columns and filtering)
- Support more advanced GenQueries with limits, offsets, and aggregations
- Query the collections and data objects within a collection
- Execute direct SQL queries
- Execute iRODS rules
- Support read, write, and seek operations for files
- PUT/GET data objects
- Create collections
- Rename collections
- Delete collections
- Create data objects
- Rename data objects
- Delete data objects
- Register files and directories
- Query metadata for collections and data objects
- Add, edit, remove metadata
- Replicate data objects to different resource servers
- Connection pool management
- Implement GenQuery result sets as lazy queries
- Return empty result sets when CAT_NO_ROWS_FOUND is raised
- Manage permissions
- Manage users and groups
- Manage resources
- Unicode strings
- Ticket based access
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


Establishing a (secure) connection
----------------------------------

Using environment files (including any SSL settings) in ``~/.irods/``:

>>> import os
>>> import ssl
>>> from irods.session import iRODSSession
>>> try:
...     env_file = os.environ['IRODS_ENVIRONMENT_FILE']
... except KeyError:
...     env_file = os.path.expanduser('~/.irods/irods_environment.json')
...
>>> ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=None, capath=None, cadata=None)
>>> ssl_settings = {'ssl_context': ssl_context}
>>> with iRODSSession(irods_env_file=env_file, **ssl_settings) as session:
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

To enumerate AVU's on an object. With no metadata attached, the result is an empty list:


>>> from irods.meta import iRODSMeta
>>> obj = session.data_objects.get("/tempZone/home/rods/test1")
>>> print(obj.metadata.items())
[]


We then add some metadata.
Just as with the icommand equivalent "imeta add ...", we can add multiple AVU's with the same name field:


>>> obj.metadata.add('key1', 'value1', 'units1')
>>> obj.metadata.add('key1', 'value2')
>>> obj.metadata.add('key2', 'value3')
>>> obj.metadata.add('key2', 'value4')
>>> print(obj.metadata.items())
[<iRODSMeta 13182 key1 value1 units1>, <iRODSMeta 13185 key2 value4 None>,
<iRODSMeta 13183 key1 value2 None>, <iRODSMeta 13184 key2 value3 None>]


We can also use Python's item indexing syntax to perform the equivalent of an "imeta set ...", e.g. overwriting
all AVU's with a name field of "key2" in a single update:


>>> new_meta = iRODSMeta('key2','value5','units2')
>>> obj.metadata[new_meta.name] = new_meta
>>> print(obj.metadata.items())
[<iRODSMeta 13182 key1 value1 units1>, <iRODSMeta 13183 key1 value2 None>,
 <iRODSMeta 13186 key2 value5 units2>]


Now, with only one AVU on the object with a name of "key2", *get_one* is assured of not throwing an exception:


>>> print(obj.metadata.get_one('key2'))
<iRODSMeta 13186 key2 value5 units2>


However, the same is not true of "key1":


>>> print(obj.metadata.get_one('key1'))
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/[...]/python-irodsclient/irods/meta.py", line 41, in get_one
    raise KeyError
KeyError


Finally, to remove a specific AVU from an object:


>>> obj.metadata.remove('key1', 'value1', 'units1')
>>> print(obj.metadata.items())
[<iRODSMeta 13186 key2 value5 units2>, <iRODSMeta 13183 key1 value2 None>]


Alternately, this form of the remove() method can also be useful:


>>> for avu in obj.metadata.items():
...    obj.metadata.remove(avu)
>>> print(obj.metadata.items())
[]


If we intended on deleting the data object anyway, we could have just done this instead:


>>> obj.unlink(force=True)


But notice that the force option is important, since a data object in the trash may still have AVU's attached.

At the end of a long session of AVU add/manipulate/delete operations, one should make sure to delete all unused
AVU's. We can in fact use any *\*Meta* data model in the queries below, since unattached AVU's are not aware
of the (type of) catalog object they once annotated:


>>> from irods.models import (DataObjectMeta, ResourceMeta)
>>> len(list( session.query(ResourceMeta) ))
4
>>> from irods.test.helpers import remove_unused_metadata
>>> remove_unused_metadata(session)
>>> len(list( session.query(ResourceMeta) ))
0


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

Query using other models:

>>> from irods.column import Criterion
>>> from irods.models import DataObject, DataObjectMeta, Collection, CollectionMeta
>>> from irods.session import iRODSSession
>>> import os
>>> env_file = os.path.expanduser('~/.irods/irods_environment.json')
>>> with iRODSSession(irods_env_file=env_file) as session:
...    # by metadata
...    # equivalent to 'imeta qu -C type like Project'
...    results = session.query(Collection, CollectionMeta).filter( \
...        Criterion('=', CollectionMeta.name, 'type')).filter( \
...        Criterion('like', CollectionMeta.value, '%Project%'))
...    for r in results:
...        print(r[Collection.name], r[CollectionMeta.name], r[CollectionMeta.value], r[CollectionMeta.units])
...
('/tempZone/home/rods', 'type', 'Project', None)

Beginning with version 0.8.3 of PRC, the 'in' genquery operator is also available:

>>> from irods.models import Resource
>>> from irods.column import In
>>> [ resc[Resource.id]for resc in session.query(Resource).filter(In(Resource.name, ['thisResc','thatResc'])) ]
[10037,10038]

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


Instantiating iRODS objects from query results
----------------------------------------------
The General query works well for getting information out of the ICAT if all we're interested in is
information representable with
primitive types (ie. object names, paths, and ID's, as strings or integers). But Python's object orientation also
allows us to create object references to mirror the persistent entities (instances of *Collection*, *DataObject*, *User*, or *Resource*, etc.)
inhabiting the ICAT.

**Background:**
Certain iRODS object types can be instantiated easily using the session object's custom type managers,
particularly if some parameter (often just the name or path) of the object is already known:

>>> type(session.users)
<class 'irods.manager.user_manager.UserManager'>
>>> u = session.users.get('rods')
>>> u.id
10003

Type managers are good for specific operations, including object creation and removal::

>>> session.collections.create('/tempZone/home/rods/subColln')
>>> session.collections.remove('/tempZone/home/rods/subColln')
>>> session.data_objects.create('/tempZone/home/rods/dataObj')
>>> session.data_objects.unlink('/tempZone/home/rods/dataObj')

When we retrieve a reference to an existing collection using *get* :

>>> c = session.collections.get('/tempZone/home/rods')
>>> c
<iRODSCollection 10011 rods>


we have, in that variable *c*, a reference to an iRODS *Collection* object whose properties provide
useful information:

>>> [ x for x in dir(c) if not x.startswith('__') ]
['_meta', 'data_objects', 'id', 'manager', 'metadata', 'move', 'name', 'path', 'remove', 'subcollections', 'unregister', 'walk']
>>> c.name
'rods'
>>> c.path
'/tempZone/home/rods'
>>> c.data_objects
[<iRODSDataObject 10019 test1>]
>>> c.metadata.items()
[ <... list of AVU's attached to Collection c ... > ]

or whose methods can do useful things:

>>> for sub_coll in c.walk(): print('---'); pprint( sub_coll )
[ ...< series of Python data structures giving the complete tree structure below collection 'c'> ...]

This approach of finding objects by name, or via their relations with other objects (ie "contained by", or in the case of metadata, "attached to"),
is helpful if we know something about the location or identity of what we're searching for, but we don't always
have that kind of a-priori knowledge.

So, although we can (as seen in the last example) walk an *iRODSCollection* recursively to discover all subordinate
collections and their data objects, this approach will not always be best
for a given type of application or data discovery, especially in more advanced
use cases.

**A Different Approach:**
For the PRC to be sufficiently powerful for general use, we'll often need at least:

* general queries, and
* the capabilities afforded by the PRC's object-relational mapping.

Suppose, for example, we wish to enumerate all collections in the iRODS catalog.

Again, the object managers are the answer, but they are now invoked using a different scheme:

>>> from irods.collection import iRODSCollection; from irods.models import Collection
>>> all_collns = [ iRODSCollection(session.collections,result) for result in session.query(Collection) ]

From there, we have the ability to do useful work, or filtering based on the results of the enumeration.
And, because *all_collns* is an iterable of true objects, we can either use Python's list comprehensions or
execute more catalog queries to achieve further aims.

Note that, for similar system-wide queries of Data Objects (which, as it happens, are inextricably joined to their
parent Collection objects), a bit more finesse is required.  Let us query, for example, to find all data
objects in a particular zone with an AVU that matches the following condition::

   META_DATA_ATTR_NAME = "irods::alert_time" and META_DATA_ATTR_VALUE like '+0%'
   
   
>>> import irods.keywords
>>> from irods.data_object import iRODSDataObject
>>> from irods.models import DataObjectMeta, DataObject
>>> from irods.column import Like
>>> q = session.query(DataObject).filter( DataObjectMeta.name == 'irods::alert_time',
                                          Like(DataObjectMeta.value, '+0%') )
>>> zone_hint = "" # --> add a zone name in quotes to search another zone
>>> if zone_hint: q = q.add_keyword( irods.keywords.ZONE_KW, zone_hint )
>>> for res in q:
...      colln_id = res [DataObject.collection_id]
...      collObject = get_collection( colln_id, session, zone = zone_hint)
...      dataObject = iRODSDataObject( session.data_objects, parent = collObject, results=[res])
...      print( '{coll}/{data}'.format (coll = collObject.path, data = dataObject.name))


In the above loop we have used a helper function, *get_collection*, to minimize the number of hits to the object
catalog. Otherwise, me might find within a typical application  that some Collection objects are being queried at
a high rate of redundancy. *get_collection* can be implemented thusly:

.. code:: Python

    import collections  # of the Pythonic, not iRODS, kind
    def makehash():
        # see https://stackoverflow.com/questions/651794/whats-the-best-way-to-initialize-a-dict-of-dicts-in-python
        return collections.defaultdict(makehash)
    from irods.collection import iRODSCollection
    from irods.models import Collection
    def get_collection (Id, session, zone=None, memo = makehash()):
        if not zone: zone = ""
        c_obj = memo[session][zone].get(Id)
        if c_obj is None:
            q = session.query(Collection).filter(Collection.id==Id)
            if zone != '': q = q.add_keyword( irods.keywords.ZONE_KW, zone )
            c_id =  q.one()
            c_obj = iRODSCollection(session, result = c_id)
            memo[session][zone][Id] = c_obj
        return c_obj


Once instantiated, of course, any *iRODSDataObject*'s data to which we have access permissions is available via its open() method.

As stated, this type of object discovery requires some extra study and effort, but the ability to search arbitrary iRODS zones
(to which we are federated and have the user permissions) is powerful indeed.


Tracking and manipulating replicas of Data objects
--------------------------------------------------

Putting together the techniques we've seen so far, it's not hard to write functions
that achieve useful, common goals. Suppose that for all data objects containing replicas on
a given named resource (the "source") we want those replicas "moved" to a second, or
"destination" resource.  We can achieve it with a function such as the one below. It
achieves the move via a replication of the data objects found to the destination
resource , followed by a trimming of each replica from the source.  We assume for our current
purposed that all replicas are "good", ie have a status of "1" ::

  from irods.resource import iRODSResource
  from irods.collection import iRODSCollection
  from irods.data_object import iRODSDataObject
  from irods.models import Resource,Collection,DataObject
  def repl_and_trim (srcRescName, dstRescName = '', verbose = False):
      objects_trimmed = 0
      q = session.query(Resource).filter(Resource.name == srcRescName)
      srcResc = iRODSResource( session.resources, q.one())
      # loop over data objects found on srcResc
      for q_row in session.query(Collection,DataObject) \
                          .filter(DataObject.resc_id == srcResc.id):
          collection =  iRODSCollection (session.collections, result = q_row)
          data_object = iRODSDataObject (session.data_objects, parent = collection, results = (q_row,))
          objects_trimmed += 1
          if verbose :
              import pprint
              print( '--------', data_object.name, '--------')
              pprint.pprint( [vars(r) for r in data_object.replicas if
                              r.resource_name == srcRescName] )
          if dstRescName:
              objects_trimmed += 1
              data_object.replicate(dstRescName)
              for replica_number in [r.number for r in data_object.replicas]:
                  options = { kw.DATA_REPL_KW: replica_number }
                  data_object.unlink( **options )
      return objects_trimmed


Listing Users and Groups ; calculating Group Membership
-------------------------------------------------------

iRODS tracks groups and users using two tables, R_USER_MAIN and R_USER_GROUP.
Under this database schema, all "user groups" are also users:

>>> from irods.models import User, UserGroup
>>> from pprint import pprint
>>> pprint(list( [ (x[User.id], x[User.name]) for x in session.query(User) ] ))
[(10048, 'alice'),
 (10001, 'rodsadmin'),
 (13187, 'bobby'),
 (10045, 'collab'),
 (10003, 'rods'),
 (13193, 'empty'),
 (10002, 'public')]

But it's also worth noting that the User.type field will be 'rodsgroup' for any
user ID that iRODS internally recognizes as a "Group":

>>> groups = session.query(User).filter( User.type == 'rodsgroup' )

>>> [x[User.name] for x in groups]
['collab', 'public', 'rodsadmin', 'empty']

Since we can instantiate iRODSUserGroup and iRODSUser objects directly from the rows of
a general query on the corresponding tables,  it is also straightforward to trace out
the groups' memberships:

>>> from irods.user import iRODSUser, iRODSUserGroup
>>> grp_usr_mapping = [ (iRODSUserGroup ( session.user_groups, result), iRODSUser (session.users, result)) \
...                     for result in session.query(UserGroup,User) ]
>>> pprint( [ (x,y) for x,y in grp_usr_mapping if x.id != y.id ] )
[(<iRODSUserGroup 10045 collab>, <iRODSUser 10048 alice rodsuser tempZone>),
 (<iRODSUserGroup 10001 rodsadmin>, <iRODSUser 10003 rods rodsadmin tempZone>),
 (<iRODSUserGroup 10002 public>, <iRODSUser 10003 rods rodsadmin tempZone>),
 (<iRODSUserGroup 10002 public>, <iRODSUser 10048 alice rodsuser tempZone>),
 (<iRODSUserGroup 10045 collab>, <iRODSUser 13187 bobby rodsuser tempZone>),
 (<iRODSUserGroup 10002 public>, <iRODSUser 13187 bobby rodsuser tempZone>)]

(Note that in general queries, fields cannot be compared to each other, only to literal constants; thus
the '!=' comparison in the Python list comprehension.)

From the above, we can see that the group 'collab' (with user ID 10045) contains users 'bobby'(13187) and
'alice'(10048) but not 'rods'(10003), as the tuple (10045,10003) is not listed. Group 'rodsadmin'(10001)
contains user 'rods'(10003) but no other users; and group 'public'(10002) by default contains all canonical
users (those whose User.type is 'rodsadmin' or 'rodsuser'). The empty group ('empty') has no users as
members, so it doesn't show up in our final list.


Getting and setting permissions
-------------------------------

We can find the ID's of all the collections writable (ie having "modify" ACL) by, but not owned by,
alice (or even alice#otherZone):

>>> from irods.models import Collection,CollectionAccess,CollectionUser,User
>>> from irods.column import Like
>>> q = session.query (Collection,CollectionAccess).filter(
...                                 CollectionUser.name == 'alice',  # User.zone == 'otherZone', # zone optional
...                                 Like(CollectionAccess.name, 'modify%') ) #defaults to current zone

If we then want to downgrade those permissions to read-only, we can do the following:

>>> from irods.access import iRODSAccess
>>> for c in q:
...     session.permissions.set( iRODSAccess('read', c[Collection.name], 'alice', # 'otherZone' # zone optional
...     ))

We can also query on access type using its numeric value, which will seem more natural to some:

>>> OWN = 1200; MODIFY = 1120 ; READ = 1050
>>> from irods.models import DataAccess, DataObject, User
>>> data_objects_writable = list(session.query(DataObject,DataAccess,User)).filter(User.name=='alice',  DataAccess.type >= MODIFY)


And more...
-----------

Additional code samples are available in the `test directory <https://github.com/irods/python-irodsclient/tree/master/irods/test>`_
