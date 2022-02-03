=========================
Python iRODS Client (PRC)
=========================

`iRODS <https://www.irods.org>`_ is an open source distributed data management system. This is a client API implemented in Python.

Currently supported:

- Python 2.7, 3.4 or newer
- Establish a connection to iRODS
- Authenticate via password, GSI, PAM
- iRODS connection over SSL
- Implement basic GenQueries (select columns and filtering)
- Support more advanced GenQueries with limits, offsets, and aggregations
- Query the collections and data objects within a collection
- Execute direct SQL queries
- Execute iRODS rules
- Support read, write, and seek operations for files
- Parallel PUT/GET data objects
- Create collections
- Rename collections
- Delete collections
- Create data objects
- Rename data objects
- Checksum data objects
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


Installing
----------

PRC requires Python 2.7 or 3.4+.
Canonically, to install with pip::

 pip install python-irodsclient

or::

 pip install git+https://github.com/irods/python-irodsclient.git[@branch|@commit|@tag]

Uninstalling
------------

::

 pip uninstall python-irodsclient

Hazard: Outdated Python
--------------------------
With older versions of Python (as of this writing, the aforementioned 2.7 and 3.4), we
can take preparatory steps toward securing workable versions of pip and virtualenv by
using these commands::

    $ pip install --upgrade --user pip'<21.0'
    $ python -m pip install --user virtualenv

We are then ready to use any of the following commands relevant to and required for the
installation::

    $ python -m virtualenv ... 
    $ python -m pip install ...


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
...     # workload
...
>>>

Passing iRODS credentials as keyword arguments:

>>> from irods.session import iRODSSession
>>> with iRODSSession(host='localhost', port=1247, user='bob', password='1234', zone='tempZone') as session:
...     # workload
...
>>>

If you're an administrator acting on behalf of another user:

>>> from irods.session import iRODSSession
>>> with iRODSSession(host='localhost', port=1247, user='rods', password='1234', zone='tempZone',
           client_user='bob', client_zone='possibly_another_zone') as session:
...     # workload
...
>>>

If no ``client_zone`` is provided, the ``zone`` parameter is used in its place.

A pure Python SSL session (without a local `env_file`) requires a few more things defined:

>>> import ssl
>>> from irods.session import iRODSSession 
>>> ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile='CERTNAME.crt', capath=None, cadata=None)
>>> ssl_settings = {'client_server_negotiation': 'request_server_negotiation',
...                'client_server_policy': 'CS_NEG_REQUIRE',
...                'encryption_algorithm': 'AES-256-CBC',
...                'encryption_key_size': 32,
...                'encryption_num_hash_rounds': 16,
...                'encryption_salt_size': 8,                        
...                'ssl_context': ssl_context}
>>>
>>> with iRODSSession(host='HOSTNAME_DEFINED_IN_CAFILE_ABOVE', port=1247, user='bob', password='1234', zone='tempZone', **ssl_settings) as session:
...	# workload
>>>


Maintaining a connection
------------------------

The default library timeout for a connection to an iRODS Server is 120 seconds.

This can be overridden by changing the session `connection_timeout` immediately after creation of the session object:

>>> session.connection_timeout = 300

This will set the timeout to five minutes for any associated connections.

Session objects and cleanup
---------------------------

When iRODSSession objects are kept as state in an application, spurious SYS_HEADER_READ_LEN_ERR errors
can sometimes be seen in the connected iRODS server's log file. This is frequently seen at program exit
because socket connections are terminated without having been closed out by the session object's 
cleanup() method.

Starting with PRC Release 0.9.0, code has been included in the session object's __del__ method to call
cleanup(), properly closing out network connections.  However, __del__ cannot be relied to run under all
circumstances (Python2 being more problematic), so an alternative may be to call session.cleanup() on
any session variable which might not be used again.


Simple PUTs and GETs
--------------------

We can use the just-created session object to put files to (or get them from) iRODS.

>>> logical_path = "/{0.zone}/home/{0.username}/{1}".format(session,"myfile.dat")
>>> session.data_objects.put( "myfile.dat", logical_path)
>>> session.data_objects.get( logical_path, "/tmp/myfile.dat.copy" )

Note that local file paths may be relative, but iRODS data objects must always be referred to by
their absolute paths.  This is in contrast to the ``iput`` and ``iget`` icommands, which keep
track of the current working collection (as modified by ``icd``) for the unix shell.


Parallel Transfer
-----------------

Starting with release 0.9.0, data object transfers using put() and get() will spawn a number
of threads in order to optimize performance for iRODS server versions 4.2.9+ and file sizes
larger than a default threshold value of 32 Megabytes.


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


Specifying paths
----------------

Path strings for collection and data objects are usually expected to be absolute in most contexts in the PRC. They
must also be normalized to a form including single slashes separating path elements and no slashes at the string's end.
If there is any doubt that a path string fulfills this requirement, the wrapper class :code:`irods.path.iRODSPath`
(a subclass of :code:`str`) may be used to normalize it::

    if not session.collections.exists( iRODSPath( potentially_unnormalized_path )): #....

The wrapper serves also as a path joiner; thus::

    iRODSPath( zone, "home", user )

may replace::

    "/".join(["", zone, "home", user])

:code:`iRODSPath` is available beginning with PRC release :code:`v1.1.2`.


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


Computing and Retrieving Checksums
----------------------------------

Each data object may be associated with a checksum by calling chksum() on the object in question.  Various
behaviors can be elicited by passing in combinations of keywords (for a description of which, please consult the
`header documentation <https://github.com/irods/irods/blob/4-2-stable/lib/api/include/dataObjChksum.h>`_ .)

As with most other iRODS APIs, it is straightforward to specify keywords by adding them to an option dictionary:

>>> data_object_1.chksum()  # - computes the checksum if already in the catalog, otherwise computes and stores it
...                         #   (ie. default behavior with no keywords passed in.)
>>> from irods.manager.data_object_manager import Server_Checksum_Warning
>>> import irods.keywords as kw
>>> opts = { kw.VERIFY_CHKSUM_KW:'' }
>>> try:
...     data_object_2.chksum( **opts )  # - Uses verification option. (Does not auto-vivify a checksum field).
...     # or:
...     opts[ kw.NO_COMPUTE_KW ] = ''
...     data_object_2.chksum( **opts )  # - Uses both verification and no-compute options. (Like ichksum -K --no-compute)
... except Server_Checksum_Warning:
...     print('some checksums are missing or wrong')

Additionally, if a freshly created irods.message.RErrorStack instance is given, information can be returned and read by
the client:

>>> r_err_stk = RErrorStack()
>>> warn = None
>>> try:  # Here, data_obj has one replica, not yet checksummed.
...     data_obj.chksum( r_error = r_err_stk , **{kw.VERIFY_CHKSUM_KW:''} )
... except Server_Checksum_Warning as exc:
...     warn = exc
>>> print(r_err_stk)
[RError<message = u'WARNING: No checksum available for replica [0].', status = -862000 CAT_NO_CHECKSUM_FOR_REPLICA>]


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


Atomic operations on metadata
-----------------------------

With release 4.2.8 of iRODS, the atomic metadata API was introduced to allow a group of metadata add and remove
operations to be performed transactionally, within a single call to the server.  This capability can be leveraged in
version 0.8.6 of the PRC.

So, for example, if 'obj' is a handle to an object in the iRODS catalog (whether a data object, collection, user or
storage resource), we can send an arbitrary number of AVUOperation instances to be executed together as one indivisible
operation on that object:

>>> from irods.meta import iRODSMeta, AVUOperation
>>> obj.metadata.apply_atomic_operations( AVUOperation(operation='remove', avu=iRODSMeta('a1','v1','these_units')),
...                                       AVUOperation(operation='add', avu=iRODSMeta('a2','v2','those_units')),
...                                       AVUOperation(operation='remove', avu=iRODSMeta('a3','v3')) # , ...
... )

The list of operations will applied in the order given, so that a "remove" followed by an "add" of the same AVU
is, in effect, a metadata "set" operation.  Also note that a "remove" operation will be ignored if the AVU value given
does not exist on the target object at that point in the sequence of operations.

We can also source from a pre-built list of AVUOperations using Python's `f(*args_list)` syntax. For example, this
function uses the atomic metadata API to very quickly remove all AVUs from an object:

>>> def remove_all_avus( Object ):
...     avus_on_Object = Object.metadata.items()
...     Object.metadata.apply_atomic_operations( *[AVUOperation(operation='remove', avu=i) for i in avus_on_Object] )


Special Characters
------------------

Of course, it is fine to put Unicode characters into your collection and data object names.  However, certain
non-printable ASCII characters, and the backquote character as well, have historically presented problems -
especially for clients using iRODS's human readable XML protocol.  Consider this small, only slighly contrived,
application:
::

    from irods.test.helpers import make_session

    def create_notes( session, obj_name, content = u'' ):
        get_home_coll = lambda ses: "/{0.zone}/home/{0.username}".format(ses)
        path = get_home_coll(session) + "/" + obj_name
        with session.data_objects.open(path,"a") as f:
            f.seek(0, 2) # SEEK_END
            f.write(content.encode('utf8'))
        return session.data_objects.get(path)

    with make_session() as session:

        # Example 1 : exception thrown when name has non-printable character
        try:
            create_notes( session, "lucky\033.dat", content = u'test' )
        except:
            pass

        # Example 2 (Ref. issue: irods/irods #4132, fixed for 4.2.9 release of iRODS)
        print(
            create_notes( session, "Alice`s diary").name  # note diff (' != `) in printed name
        )


This creates two data objects, but with less than optimal success.  The first example object
is created but receives no content because an exception is thrown trying to query its name after
creation.   In the second example, for iRODS 4.2.8 and before, a deficiency in packStruct XML protocol causes
the backtick to be read back as an apostrophe, which could create problems manipulating or deleting the object later.

As of PRC v1.1.0, we can mitigate both problems by switching in the QUASI_XML parser for the default one:
::

    from irods.message import (XML_Parser_Type, ET)
    ET( XML_Parser.QUASI_XML, session.server_version )

Two dedicated environment variables may also be used to customize the Python client's XML parsing behavior via the
setting of global defaults during start-up.

For example, we can set the default parser to QUASI_XML, optimized for use with version 4.2.8 of the iRODS server,
in the following manner:
::

    Bash-Shell> export PYTHON_IRODSCLIENT_DEFAULT_XML=QUASI_XML PYTHON_IRODSCLIENT_QUASI_XML_SERVER_VERSION=4,2,8

Other alternatives for PYTHON_IRODSCLIENT_DEFAULT_XML are "STANDARD_XML" and "SECURE_XML".  These two latter options
denote use of the xml.etree and defusedxml modules, respectively.

Only the choice of "QUASI_XML" is affected by the specification of a particular server version.

Finally, note that these global defaults, once set, may be overridden on a per-thread basis using
:code:`ET(parser_type, server_version)`.  We can also revert the current thread's XML parser back to the
global default by calling :code:`ET(None)`.


Rule Execution
--------------

A simple example of how to execute an iRODS rule from the Python client is as follows.  Suppose we have a rule file
:code:`native1.r` which contains a rule in native iRODS Rule Language::

  main() {
      writeLine("*stream",
                *X ++ " squared is " ++ str(double(*X)^2) )
  }

  INPUT *X="3", *stream="serverLog"
  OUTPUT null

The following Python client code will run the rule and produce the appropriate output in the
irods server log::

  r = irods.rule.Rule( session, rule_file = 'native1.r')
  r.execute()

With release v1.1.1, not only can we target a specific rule engine instance by name (which is useful when
more than one is present), but we can also use a file-like object for the :code:`rule_file` parameter::

  Rule( session, rule_file = io.StringIO(u'''mainRule() { anotherRule(*x); writeLine('stdout',*x) }\n'''
                                         u'''anotherRule(*OUT) {*OUT='hello world!'}\n\n'''
                                         u'''OUTPUT ruleExecOut\n'''),
        instance_name = 'irods_rule_engine_plugin-irods_rule_language-instance' )

Incidentally, if we wanted to change the :code:`native1.r` rule code print to stdout also, we could set the
:code:`INPUT` parameter, :code:`*stream`, using the Rule constructor's :code:`params` keyword argument.
Similarly, we can change the :code:`OUTPUT` parameter from :code:`null` to :code:`ruleExecOut`, to accommodate
the output stream, via the :code:`output` argument::

  r = irods.rule.Rule( session, rule_file = 'native1.r',
             instance_name = 'irods_rule_engine_plugin-irods_rule_language-instance',
             params={'*stream':'"stdout"'} , output = 'ruleExecOut' )
  output = r.execute( )
  if output and len(output.MsParam_PI):
      buf = output.MsParam_PI[0].inOutStruct.stdoutBuf.buf
      if buf: print(buf.rstrip(b'\0').decode('utf8'))

(Changing the input value to be squared in this example is left as an exercise for the reader!)

To deal with errors resulting from rule execution failure, two approaches can be taken. Suppose we
have defined this in the :code:`/etc/irods/core.re` rule-base::

  rule_that_fails_with_error_code(*x) {
    *y = (if (*x!="") then int(*x) else 0)
  # if (SOME_PROCEDURE_GOES_WRONG) {
      if (*y < 0) { failmsg(*y,"-- my error message --"); }  #-> throws an error code of int(*x) in REPF
      else { fail(); }                                       #-> throws FAIL_ACTION_ENCOUNTERED_ERR in REPF
  # }
  }

We can run the rule thus:

>>> Rule( session, body='rule_that_fails_with_error_code(""), instance_name = 'irods_rule_engine_plugin-irods_rule_language-instance',
...     ).execute( r_error = (r_errs:= irods.message.RErrorStack()) )

Where we've used the Python 3.8 "walrus operator" for brevity.  The error will automatically be caught and translated to a
returned-error stack::

  >>> pprint.pprint([vars(r) for r in r_errs])
  [{'raw_msg_': 'DEBUG: fail action encountered\n'
                'line 14, col 15, rule base core\n'
                '        else { fail(); }\n'
                '               ^\n'
                '\n',
    'status_': -1220000}]

Note, if a stringized negative integer is given , ie. as a special fail code to be thrown within the rule,
we must add this code into a special parameter to have this automatically caught as well:

>>> Rule( session, body='rule_that_fails_with_error_code("-2")',instance_name = 'irods_rule_engine_plugin-irods_rule_language-instance'
...     ).execute( acceptable_errors = ( FAIL_ACTION_ENCOUNTERED_ERR, -2),
...                r_error = (r_errs := irods.message.RErrorStack()) )

Because the rule is written to emit a custom error message via failmsg in this case, the resulting r_error stack will now include that
custom error message as a substring::

  >>> pprint.pprint([vars(r) for r in r_errs])
  [{'raw_msg_': 'DEBUG: -- my error message --\n'
                'line 21, col 20, rule base core\n'
                '      if (*y < 0) { failmsg(*y,"-- my error message --"); }  '
                '#-> throws an error code of int(*x) in REPF\n'
                '                    ^\n'
                '\n',
    'status_': -1220000}]

Alternatively, or in combination with the automatic catching of errors, we may also catch errors as exceptions on the client
side.  For example, if the Python rule engine is configured, and the following rule is placed in :code:`/etc/irods/core.py`::

  def python_rule(rule_args, callback, rei):
  #   if some operation fails():
          raise RuntimeError

we can trap the error thus::

  try:
      Rule( session, body = 'python_rule', instance_name = 'irods_rule_engine_plugin-python-instance' ).execute()
  except irods.exception.RULE_ENGINE_ERROR:
      print('Rule execution failed!')
      exit(1)
  print('Rule execution succeeded!')

As fail actions from native rules are not thrown by default (refer to the help text for :code:`Rule.execute`), if we
anticipate these and prefer to catch them as exceptions, we can do it this way::

  try:
      Rule( session, body = 'python_rule', instance_name = 'irods_rule_engine_plugin-python-instance'
           ).execute( acceptable_errors = () )
  except (irods.exception.RULE_ENGINE_ERROR,
          irods.exception.FAIL_ACTION_ENCOUNTERED_ERR) as e:
      print('Rule execution failed!')
      exit(1)
  print('Rule execution succeeded!')

Finally,  keep in mind that rule code submitted through an :code:`irods.rule.Rule` object is processed by the
exec_rule_text function in the targeted plugin instance.  This may be a limitation for plugins not equipped to
handle rule code in this way.  In a sort of middle-ground case, the iRODS Python Rule Engine Plugin is not
currently able to handle simple rule calls and the manipulation of iRODS core primitives (like simple parameter
passing and variable expansion') as flexibly as the iRODS Rule Language.

Also, core.py rules may not be run directly (as is also true with :code:`irule`) by other than a rodsadmin user
pending the resolution of `this issue <https://github.com/irods/irods_rule_engine_plugin_python/issues/105>`_.


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


Tickets
-------

The :code:`irods.ticket.Ticket` class lets us issue "tickets" which grant limited
permissions for other users to access our own data objects (or collections of
data objects).   As with the iticket client, the access may be either "read"
or "write".  The recipient of the ticket could be a rodsuser, or even an
anonymous user.

Below is a demonstration of how to generate a new ticket for access to a
logical path - in this case, say a collection containing 1 or more data objects.
(We assume the creation of the granting_session and receiving_session for the users
respectively for the users providing and consuming the ticket access.)

The user who wishes to provide an access may execute the following:

>>> from irods.ticket import Ticket
>>> new_ticket = Ticket (granting_session)
>>> The_Ticket_String = new_ticket.issue('read', 
...     '/zone/home/my/collection_with_data_objects_for/somebody').string

at which point that ticket's unique string may be given to other users, who can then apply the
ticket to any existing session object in order to gain access to the intended object(s):

>>> from irods.models import Collection, DataObject
>>> ses = receiving_session
>>> Ticket(ses, The_Ticket_String).supply()
>>> c_result = ses.query(Collection).one()
>>> c = iRODSCollection( ses.collections, c_result)
>>> for dobj in (c.data_objects):
...     ses.data_objects.get( dobj.path, '/tmp/' + dobj.name ) # download objects

In this case, however, modification will not be allowed because the ticket is for read only:

>>> c.data_objects[0].open('w').write(  # raises
...     b'new content')                 #  CAT_NO_ACCESS_PERMISSION

In another example, we could generate a ticket that explicitly allows 'write' access on a
specific data object, thus granting other users the permissions to modify as well as read it:

>>> ses = iRODSSession( user = 'anonymous', password = '', host = 'localhost',
                        port = 1247, zone = 'tempZone')
>>> Ticket(ses, write_data_ticket_string ).supply()
>>> d_result = ses.query(DataObject.name,Collection.name).one()
>>> d_path = ( d_result[Collection.name] + '/' +
...            d_result[DataObject.name] )
>>> old_content = ses.data_objects.open(d_path,'r').read()
>>> with tempfile.NamedTemporaryFile() as f:
...     f.write(b'blah'); f.flush()
...     ses.data_objects.put(f.name,d_path)

As with iticket, we may set a time limit on the availability of a ticket, either as a
timestamp or in seconds since the epoch:

>>> t=Ticket(ses); s = t.string
vIOQ6qzrWWPO9X7
>>> t.issue('read','/some/path')
>>> t.modify('expiry','2021-04-01.12:34:56')  # timestamp assumed as UTC

To check the results of the above, we could invoke this icommand elsewhere in a shell prompt:

:code:`iticket ls vIOQ6qzrWWPO9X7`

and the server should report back the same expiration timestamp.

And, if we are the issuer of a ticket, we may also query, filter on, and
extract information based on a ticket's attributes and catalog relations:

>>> from irods.models import TicketQuery
>>> delay = lambda secs: int( time.time() + secs + 1)
>>> Ticket(ses).issue('read','/path/to/data_object').modify(
                      'expiry',delay(7*24*3600))             # lasts 1 week
>>> Q = ses.query (TicketQuery.Ticket, TicketQuery.DataObject).filter(
...                                                            TicketQuery.DataObject.name == 'data_object')
>>> print ([ _[TicketQuery.Ticket.expiry_ts] for _ in Q ])
['1636757427']


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


Managing users
--------------

You can create a user in the current zone (with an optional auth_str):

>>> session.users.create('user', 'rodsuser', 'MyZone', auth_str)

If you want to create a user in a federated zone, use:

>>> session.users.create('user', 'rodsuser', 'OtherZone', auth_str)


And more...
-----------

Additional code samples are available in the `test directory <https://github.com/irods/python-irodsclient/tree/main/irods/test>`_


=======
Testing
=======

Setting up and running tests
----------------------------

The Python iRODS Client comes with its own suite of tests.  Some amount of setting up may be necessary first:

1. Use :code:`iinit` to specify the iRODS client environment.
   For best results, point the client at a server running on the local host.

2. Install the python-irodsclient along with the :code:`unittest unittest_xml_reporting` module or the older :code:`xmlrunner` equivalent.

   - for PRC versions 1.1.1 and later:

     *  :code:`pip install ./path-to-python-irodsclient-repo[tests]`  (when using a local Git repo); or,
     *  :code:`pip install python-irodsclient[tests]'>=1.1.1'`  (when installing directly from PyPI).

   - earlier releases (<= 1.1.0) will install the outdated :code:`xmlrunner` module automatically

3. Follow further instructions in the `test directory <https://github.com/irods/python-irodsclient/tree/main/irods/test>`_


Testing S3 parallel transfer
----------------------------

System requirements::

- Ubuntu 18 user with Docker installed.
- Local instance of iRODS server running.
- Logged in sudo privileges.

Run a MinIO service::

  $ docker run -d -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ":9001"

Set up a bucket :code:`s3://irods` under MinIO::

  $ pip install awscli

  $ aws configure
  AWS Access Key ID [None]: minioadmin
  AWS Secret Access Key [None]: minioadmin
  Default region name [None]:
  Default output format [None]:

  $ aws --endpoint-url http://127.0.0.1:9000 s3 mb s3://irods

Set up s3 credentials for the iRODS s3 storage resource::

  $ sudo su - irods -c "/bin/echo -e 'minioadmin\nminioadmin' >/var/lib/irods/s3-credentials"
  $ sudo chown 600 /var/lib/irods/s3-credentials

Create the s3 storage resource::

  $ sudo apt install irods-resource-plugin-s3

As the 'irods' service account user::

  $ iadmin mkresc s3resc s3 $(hostname):/irods/ \
    "S3_DEFAULT_HOSTNAME=localhost:9000;"\
    "S3_AUTH_FILE=/var/lib/irods/s3-credentials;"\
    "S3_REGIONNAME=us-east-1;"\
    "S3_RETRY_COUNT=1;"\
    "S3_WAIT_TIME_SEC=3;"\
    "S3_PROTO=HTTP;"\
    "ARCHIVE_NAMING_POLICY=consistent;"\
    "HOST_MODE=cacheless_attached"

  $ dd if=/dev/urandom of=largefile count=40k bs=1k # create 40-megabyte test file

  $ pip install 'python-irodsclient>=1.1.2'

  $ python -c"from irods.test.helpers import make_session
              import irods.keywords as kw
              with make_session() as sess:
                  sess.data_objects.put( 'largefile',
                                         '/tempZone/home/rods/largeFile1',
                                         **{kw.DEST_RESC_NAME_KW:'s3resc'} )
                  sess.data_objects.get( '/tempZone/home/rods/largeFile1',
                                         '/tmp/largefile')"
