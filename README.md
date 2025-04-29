Python iRODS Client (PRC)
=========================

[iRODS](https://www.irods.org) is an open source distributed data management system. This is a client API implemented in Python.

Currently supported:

-   Python 3.9 or later
-   Establish a (secure) connection to iRODS
-   Authenticate via password, GSI, PAM
-   GenQuery and Specific Queries
-   GenQuery2
-   Manage collections, data objects, and permissions
    -   Checksum data objects
    -   Replicate data objects
    -   Parallel PUT/GET data objects
    -   Read, write, and seek operations
    -   Register files and directories
-   Manage users and groups
-   Manage resources
-   Manage and execute iRODS rules
-   Manage metadata
-   Manage ticket-based access

Installing
----------

Install via pip:

    pip install python-irodsclient

or:

    pip install git+https://github.com/irods/python-irodsclient.git[@branch|@commit|@tag]

Uninstalling
------------

    pip uninstall python-irodsclient

Establishing a (secure) connection
----------------------------------

One way of starting a session is to pass iRODS credentials as keyword
arguments:

```python
>>> from irods.session import iRODSSession
>>> with iRODSSession(host='localhost', port=1247, user='bob', password='1234', zone='tempZone') as session:
...      # workload
...
>>>
```

If you're an administrator acting on behalf of another user:

```python
>>> from irods.session import iRODSSession
>>> with iRODSSession(host='localhost', port=1247, user='rods', password='1234', zone='tempZone', client_user='bob',
           client_zone='possibly_another_zone') as session:
...      # workload
...
>>>
```

If no `client_zone` is provided, the `zone` parameter is used in its place.

Using environment files (including any SSL settings) in `~/.irods/`:

```python
>>> import os
>>> import ssl
>>> from irods.session import iRODSSession
>>> try:
...     env_file = os.environ['IRODS_ENVIRONMENT_FILE']
... except KeyError:
...     env_file = os.path.expanduser('~/.irods/irods_environment.json')
...
>>> ssl_settings = {} # Or, optionally: {'ssl_context': <user_customized_SSLContext>}
>>> with iRODSSession(irods_env_file=env_file, **ssl_settings) as session:
...     # workload
...
>>>
```

In the above example, an SSL connection can be made even if no
'ssl_context' argument is specified, in which case the Python client
internally generates its own SSLContext object to best match the iRODS
SSL configuration parameters (such as
"irods_ssl_ca_certificate_file", etc.) used to initialize the
iRODSSession. Those parameters can be given either in the environment
file, or in the iRODSSession constructor call as shown by the next
example.

A pure Python SSL session (without a local `env_file` requires a few more things defined:

```python
>>> import ssl
>>> from irods.session import iRODSSession
>>> ssl_settings = {'client_server_negotiation': 'request_server_negotiation',
...                'client_server_policy': 'CS_NEG_REQUIRE',
...                'encryption_algorithm': 'AES-256-CBC',
...                'encryption_key_size': 32,
...                'encryption_num_hash_rounds': 16,
...                'encryption_salt_size': 8,
...                'ssl_context': ssl_context
...                'ssl_verify_server': 'cert',
...                'ssl_ca_certificate_file': '/etc/irods/ssl/irods.crt'
... }
```

If necessary, a user may provide a custom SSLContext object; although,
as of release v1.1.6, this will rarely be required:

```python
>>> ssl_settings ['ssl_context'] = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, # ... other options
... )
```

At this point, we are ready to instantiate and use the session:

```python
>>> with iRODSSession(host='irods-provider', port=1247, user='bob', password='1234', zone='tempZone', **ssl_settings) as session:
...	# workload
```

Note that the `irods_` prefix is unnecessary when providing
the `encryption_*` and `ssl_*` options
directly to the constructor as keyword arguments, even though it is
required when they are placed in the environment file.

Creating a PAM or Native Authentication File
--------------------------------------------

The following free functions may be used to create the authentication secrets files (called
`.irodsA` per the convention of iRODS's iCommands):
   - `irods.client_init.write_native_irodsA_file`
   - `irods.client_init.write_pam_irodsA_file`

These functions can roughly be described as duplicating the "authentication" functionality of `iinit`,
provided that a valid `irods_environment.json` has already been created.

Each of the above functions can take a cleartext password and write an appropriately encoded
version of it into an authentication file in the appropriate location.  That location is
`~/.irods/.irodsA` unless the environment variable IRODS_AUTHENTICATION_FILE has been set
in the command shell to dictate an alternative file path.

As an example, here we write a native `.irodsA` file using the first of the two functions.  We
provide the one required argument, a password string which is entered interactively at the
terminal.

```bash
$ echo '{ "irods_user_name":"rods",
          ... # other parameters as needed
        }'> ~/.irods/irods_environment.json
$ python -c "import irods.client_init, getpass
irods.client_init.write_native_irodsA_file(getpass.getpass('Enter iRODS password -> '))"
```

By default, when an `.irodsA` file already exists, it will be overwritten. If however the
`overwrite` parameter is set to `False`, an exception of type `irods.client_init.irodsA_already_exists`
is raised to warn of any older `.irodsA` file that might otherwise have been overwritten.

Equivalently to the above, we can issue the following command.

```bash
$ prc_write_irodsA.py native <<<"${MY_CURRENT_IRODS_PASSWORD}"
```

The redirect may of course be left off, in which case the user is prompted for the iRODS password
and echo of the keyboard input will be suppressed, in the style of `iinit`.  Regardless of
which technique is used, no password will be visible on the terminal during or after input.

For the `pam_password` scheme, typically SSL/TLS must first be enabled to avoid sending data related
to the password - or even sending the raw password itself - over a network connection in the clear.

Thus, for `pam_password` authentication to work well, we should first ensure, when setting up the
client environment, to include within `irods_environment.json` the appropriate SSL/TLS connection
parameters.  In a pinch, `iinit` can be used to verify this prerequisite is fulfilled,
as its invocation would then create a valid `.irodsA` from merely prompting the user for their PAM password.

Once again, this can also be done using the free function directly:

```python
irods.client_init.write_pam_irodsA_file(getpass.getpass('Enter current PAM password -> '))
```

or from the Bash command shell:

```bash
$ prc_write_irodsA.py pam_password <<<"${MY_CURRENT_PAM_PASSWORD}"
```

As a final note, in the `pam_password` scheme, the default SSL requirement can be disabled.
**Warning:** Disabling the SSL requirement may cause user passwords to be sent over the network
in the clear. This should only be done for purposes of testing. Here's how to do it:

```python
from irods.auth.pam_password import ENSURE_SSL_IS_ACTIVE

session = irods.session.iRODSSession(host = "localhost", port = 1247,
                                     user = "alice", password = "test123", zone="tempZone",
                                     authentication_scheme = "pam_password")

session.set_auth_option_for_scheme('pam_password', ENSURE_SSL_IS_ACTIVE, False)

# Do something with the session:
home = session.collections.get('/tempZone/home/alice')
```

Note, however, in future releases of iRODS it is possible that extra SSL checking could be
implemented server-side, at which point the above code could not be guaranteed to work.

Legacy (iRODS 4.2-compatible) PAM authentication
------------------------------------------------

Since v2.0.0, the Python iRODS Client is able to authenticate via PAM using the same file-based client environment as the
iCommands.

Caveat for iRODS 4.3+: when upgrading from 4.2, the "irods_authentication_scheme" setting must be changed from "pam" to "pam_password" in
`~/.irods/irods_environment.json` for all file-based client environments.

To use the PRC PAM login credentials update function for the client login environment, we can set these two configuration variables:

```
legacy_auth.pam.password_for_auto_renew "my_pam_password"
legacy_auth.pam.store_password_to_environment True
```

Optionally, the `legacy_auth.pam.time_to_live_in_hours` may also be set to determine the time-to-live for the new password.
Leaving it at the default value defers this decision to the server.

Maintaining a connection
------------------------

The default library timeout for a connection to an iRODS Server is 120 seconds.

This can be overridden by changing the session `connection_timeout` immediately after creation of the
session object:

```python
>>> session.connection_timeout = 300
```

This will set the timeout to five minutes for any associated connections.

Timeouts are either a positive `int` or `float` with units of seconds, or `None`, all in accordance with their
meaning in the context of the socket module.  A value of `None` indicates timeouts are effectively
infinite in value, i.e. turned off.  Setting a session's `connection_timeout` value to 0 is disallowed
because this would cause the socket to enter non-blocking mode.

Session objects and cleanup
---------------------------

When iRODSSession objects are kept as state in an application, spurious
SYS_HEADER_READ_LEN_ERR errors can sometimes be seen in the
connected iRODS server's log file. This is frequently seen at program
exit because socket connections are terminated without having been
closed out by the session object's cleanup() method.

Since v0.9.0, code has been included in the session
object's `__del__` method to call cleanup(), properly closing out
network connections. However, `__del__`  is not guaranteed to run as
expected, so an alternative may be to call `session.cleanup()`
on any session variable which will not be used again.

Simple PUTs and GETs
--------------------

We can use the just-created session object to put files to (or get them
from) iRODS.

```python
>>> logical_path = "/{0.zone}/home/{0.username}/{1}".format(session,"myfile.dat")
>>> session.data_objects.put("myfile.dat", logical_path)
>>> session.data_objects.get(logical_path, "/tmp/myfile.dat.copy")
```

Note that local file paths may be relative, but iRODS data objects must
always be referred to by their absolute paths. This is in contrast to
the `iput` and `iget` icommands, which keep track of the current working
collection (as modified by `icd`) for the unix shell.

Note also that PRC `put()` is actually using the `open`, `write`, and `close` APIs, rather than the
iRODS PUT API directly.  This is transparent to the caller, but an administrator
should take note as this affects which policy enforcement points (PEPs) are executed
on the iRODS server.

Release v3.1.1 introduces the optional behavior of preventing a call to data object manager's `put()` or `create()`
method from succeeding if the requested data path already exists.  This will become the default in some future release,
but for now the following code can be used to enable it for the duration of
an application's run:

```python
import irods.client_configuration as config
# Prevent accidental data object overwrites in put() and create().
config.data_objects.force_create_by_default = False
config.data_objects.force_put_by_default = False
```

A more ad-hoc solution to defeat the "True" defaults is by passing `**{irods.keywords.FORCE_FLAG_KW:False}` among
the options in an individual call to `put`, or using force=False in a call to `create`.

Both solutions will be unnecessary, but still remain effective, when True-defaulting "force flag" style data overwrites
become non-default behavior and/or deprecated in a future release.

Parallel Transfer
-----------------

Since v0.9.0, data object transfers using `put()` and `get()`
will spawn a number of threads in order to optimize performance for
iRODS server versions 4.2.9+ and file sizes larger than a default
threshold value of 32 Megabytes.

Progress bars
-------------

The PRC supports progress bars which function on the basis of
an "update" callback function.  In the case of a tqdm progress bar (see https://github.com/tqdm/tqdm), you can always just
pass the update method of the progress bar instance directly to the data_object
`put` or `get` method:

```python
   pbar = tqdm.tqdm(total = data_obj.size)
   session.data_objects.get(file_name, data_obj.path, updatables = pbar.update)
```

The updatables parameter can be a list or tuple of update-enabling objects and/or bound methods.

Alternatively, the tqdm progress bar object itself can be passed in, if an adapting
function such as the following is first registered:

```python
    def adapt_tqdm(pbar, l = threading.Lock()):
        def _update(n):
            with l:
                pbar.update(n)
        return _update
    irods.manager.data_objects_manager.register_update_type( adapt_tqdm )
    session.data_objects.put( file, logical_path, updatables = [tqdm_1,tqdm_2] ) # update two tqdm's simultaneously
```

Other progress bars may be included in an updatables parameter, but may require more extensive adaptation.
For example, the ProgressBar object (from the progressbar module) also has an update method, but it
takes an up-to-date cumulative byte-count, instead of the size of an individual transfer in bytes,
as its sole parameter.  There can be other complications:  e.g. a ProgressBar instance does not allow a weak
reference to itself to be formed, which interferes with the Python iRODS Client's internal scheme of accounting
for progress bar instances "still in progress" while also preventing resource leaks.

In such cases, it is probably best to implement a wrapper for the progress
bar in question, and submit the wrapper instance as the updatable parameter.  Whether
a wrapper or the progress bar object itself is thus employed, it is recommended that the user take steps to
ensure the lifetime of the updatable instance extends beyond the time needed for the transfer to complete.

See `irods/test/data_obj_test.py` for examples of these and other subtleties of progress bar usage.

Working with collections (directories)
--------------------------------------

```python
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
```

Create a new collection:

```python
>>> coll = session.collections.create("/tempZone/home/rods/testdir")
>>> coll.id
45799
```

Working with data objects (files)
---------------------------------

Create a new data object:

```python
>>> obj = session.data_objects.create("/tempZone/home/rods/test1")
<iRODSDataObject /tempZone/home/rods/test1>
```

Get an existing data object:

```python
>>> obj = session.data_objects.get("/tempZone/home/rods/test1")
>>> obj.id 12345

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
```

Using the `put()` method rather than the `create()` method will trigger different policy enforcement points (PEPs) on the server.

Put an existing file as a new data object:

```python
>>> session.data_objects.put("test.txt", "/tempZone/home/rods/test2")
>>> obj2 = session.data_objects.get("/tempZone/home/rods/test2")
>>> obj2.id
56789
```

Specifying paths
----------------

Path strings for collection and data objects are usually expected to be
absolute in most contexts in the PRC. They must also be normalized to a
form including single slashes separating path elements and no slashes at
the string's end. If there is any doubt that a path string fulfills
this requirement, the wrapper class `irods.path.iRODSPath` (a subclass of `str`) may be used to normalize it:

    if not session.collections.exists( iRODSPath( potentially_unnormalized_path )): #....

The wrapper serves also as a path joiner; thus:

    iRODSPath( zone, "home", user )

may replace:

    "/".join(["", zone, "home", user])

`iRODSPath` has been available since v1.1.2.

Reading and writing files
-------------------------

PRC provides [file-like
objects](https://docs.python.org/3/glossary.html#term-file-object) for reading and writing files.

```python
>>> obj = session.data_objects.get("/tempZone/home/rods/test1")
>>> with obj.open('r+') as f:
...   f.write('foonbarn')
...   f.seek(0,0)
...   for line in f:
...      print(line)
...
foo
bar
```

Since v1.1.9, there is also an auto-close configuration setting for data
objects, set to `False` by default, which may be assigned
the value `True` for guaranteed auto-closing of open data
object handles at the proper time.

In a small but illustrative example, the following Python session does
not require an explicit call to `f.close()`:

```python
>>> import irods.client_configuration as config, irods.helpers as helpers
>>> config.data_objects.auto_close = True
>>> session = helpers.make_session()
>>> f = session.data_objects.open('/{0.zone}/home/{0.username}/new_object.txt'.format(session),'w')
>>> f.write(b'new content.')
```

This may be useful for Python programs in which frequent flushing of
write updates to data objects is undesirable -- with descriptors on such
objects possibly being held open for indeterminately long lifetimes --
yet the eventual application of those updates prior to the teardown of
the Python interpreter is required.

The current value of the setting is global in scope (i.e. applies to all
sessions, whenever created) and is always consulted for the creation of
any data object handle to govern that handle's cleanup behavior.

Also, alternatively, the client may opt into a special "redirect" behavior
in which data objects' `open()` method makes a new connection directly to whichever
iRODS server is found to host the selected replica.  Data reads and
writes will therefore happen on that alternate network route, instead of
through the originally-connected server.  Though not the client's default
behavior, this approach can turn out to be more efficient, particularly
if several concurrent data uploads ("puts") and downloads ("gets") are 
happening which might increase traffic on the client's main communication
route with the server.  (See, in [Python iRODS Client Settings File](#python-irods-client-settings-file),
the client configuration setting `data_objects.allow_redirect`, which may be
set to True to designate the opt-in.)

Python iRODS Client Settings File
---------------------------------

Since v1.1.9, Python iRODS client configuration can be saved in, and
loaded from, a settings file.

If the settings file exists, each of its lines contains (a) a dotted
name identifying a particular configuration setting to be assigned
within the PRC, potentially changing its runtime behavior; and (b) the
specific value, in Python "repr"-style format, that should be assigned
into it.

An example follows:

```
data_objects.auto_close True
```

New dotted names may be created following the example of the one valid
example created thus far, `data_objects.auto_close]`,
initialized in `irods/client_configuration/__init__.py`.
Each such name should correspond to a globally set value which the PRC
routinely checks when performing the affected library function.

The use of a settings file can be indicated, and the path to that file
determined, by setting the environment variable:
`PYTHON_IRODSCLIENT_CONFIGURATION_PATH`. If this variable
is present but empty, this denotes use of a default settings file path
of `~/.python-irodsclient`; if the variable's value is of
non-zero length, the value should be an absolute path to the desired settings
file location. Also, if the variable is set, auto-load of
settings will be performed, meaning that the act of importing
`irods` or any of its submodules will cause the automatic
loading of the settings from the settings file, assuming it exists.
(Failure to find the file at the indicated path will be logged as a
warning.)

If the process of loading configuration settings generates an unhandled exception,
the `irods` module will consult the value of the environment variable
`PYTHON_IRODSCLIENT_CONFIGURATION_LOAD_ERRORS_FATAL` and either (if `True`) incur
a fatal error or (if `False`) simply log it as a warning.  By default this
environment variable is taken as `False` if not set, although that is likely to
change to `True` in the future.
This decision indicates a desire by the client library's designers to flag such
errors as fatal by aborting the process if possible, rather than aquiescing silently
to an unintended consequence.  It is recommended that all client library users
set this environment variable to `True` if their applications load settings
from the environment or configuration files.

Settings can be saved and loaded manually using the `save()` and
`load()` functions in the `irods.client_configuration`
module. Each of these functions accepts an optional `file`
parameter which, if set to a non-empty string, will override the
settings file path currently "in force" (i.e., the
CONFIG_DEFAULT_PATH, as optionally overridden by the environment
variable PYTHON_IRODSCLIENT_CONFIGURATION_PATH).

Configuration settings may also be individually overridden by defining
certain environment variables:

-   Setting: Auto-close option for all data objects.
    -   Dotted Name: `data_objects.auto_close`
    -   Type: `bool`
    -   Default Value: `False`
    -   Environment Variable Override: `PYTHON_IRODSCLIENT_CONFIG__DATA_OBJECTS__AUTO_CLOSE`

-   Setting: Let a call to data object open() redirect to the server whose storage resource hosts the given object's preferred replica.
    -   Dotted Name: `data_objects.allow_redirect`
    -   Type: `bool`
    -   Default Value: `False`
    -   Environment Variable Override: `PYTHON_IRODSCLIENT_CONFIG__DATA_OBJECTS__ALLOW_REDIRECT`

-   Setting: Allow `put()` to overwrite an already existing data object by default.
    -   Dotted Name: `data_objects.force_put_by_default`
    -   Type: `bool`
    -   Default Value: `True` (as of v3.1.1, but not into perpetuity.)
    -   Environment Variable Override: `PYTHON_IRODSCLIENT_CONFIG__DATA_OBJECTS__FORCE_PUT_BY_DEFAULT`

-   Setting: Allow `create()` to overwrite an already existing data object by default.
    -   Dotted Name: `data_objects.force_create_by_default`
    -   Type: `bool`
    -   Default Value: `True` (as of v3.1.1, but not into perpetuity.)
    -   Environment Variable Override: `PYTHON_IRODSCLIENT_CONFIG__DATA_OBJECTS__FORCE_CREATE_BY_DEFAULT`

-   Setting: Whether to use legacy authentication despite the iRODS server supporting the 4.3 authentication plugin framework.
    - Dotted Name: `legacy_auth.force_legacy_auth`
    - Type: `bool`
    - Default Value: `False` (Meaning: allow the version of the connected server to determine the type of authentication used.)
    - Environment Variable Override: `PYTHON_IRODSCLIENT_CONFIG__LEGACY_AUTH__FORCE_LEGACY_AUTH`

-   Setting: Number of hours to request for the new password entry's TTL (Time To Live) when auto-renewing PAM-authenticated sessions.
    - Dotted Name: `legacy_auth.pam.time_to_live_in_hours`
    - Type: `int`
    - Default Value: `0` (Meaning: conform to server's default TTL value.)
    - Environment Variable Override: `PYTHON_IRODSCLIENT_CONFIG__LEGACY_AUTH__PAM__TIME_TO_LIVE_IN_HOURS`

-   Setting: Plaintext PAM password value, to be used when auto-renewing PAM-authenticated sessions because TTL has expired.
    - Dotted Name: `legacy_auth.pam.password_for_auto_renew`
    - Type: `str`
    - Default Value: `""` (Meaning: no password is set, and thus no automatic attempts will be made at auto-renewing PAM authentication.)
    - Environment Variable Override: `PYTHON_IRODSCLIENT_CONFIG__LEGACY_AUTH__PAM__PASSWORD_FOR_AUTO_RENEW`.  (But note that use of the environment variable could pose a threat to password security.)

-   Setting: Whether to write the (native encoded) new hashed password to the iRODS password file.  This step is only performed while auto-renewing PAM authenticated sessions.
    - Dotted Name: `legacy_auth.pam.store_password_to_environment`
    - Type: `bool`
    - Default Value: `False`
    - Environment Variable Override: `PYTHON_IRODSCLIENT_CONFIG__LEGACY_AUTH__PAM__STORE_PASSWORD_TO_ENVIRONMENT`

-   Setting: Force the use of PAM_AUTH_REQUEST_AN API for entering a new PAM password into the catalog.  This API accommodates longer passwords and avoids the step of parsing a semicolon-delimited
    "context" parameter.
    - Dotted Name: `legacy_auth.pam.force_use_of_dedicated_pam_api`
    - Type: `bool`
    - Default Value: `False`
    - Environment Variable Override: `PYTHON_IRODSCLIENT_CONFIG__LEGACY_AUTH__PAM__FORCE_USE_OF_DEDICATED_PAM_API`

-   Setting: The maximum number of rows a Query iteration will retrieve.  Can be overridden using Query's `limit` method. This is synonymous with the variable `irods.query.IRODS_QUERY_LIMIT`, and a read (or write) of this configuration setting will read (or affect) that variable.
    -   Dotted Name: `genquery1.irods_query_limit`
    -   Type: `int`
    -   Default Value: 500 (The library's traditional maximum batch row count, also stored as `irods.query._IRODS_QUERY_LIMIT`)
    -   Environment Variable Override: `PYTHON_IRODSCLIENT_CONFIG__GENQUERY1__IRODS_QUERY_LIMIT`

-   Setting: Default choice of XML parser for all new threads.
    -   Dotted Name: `connections.xml_parser_default`
    -   Type: `str`
    -   Default Value: `"STANDARD_XML"`
    -   Possible Values: Any of `["STANDARD_XML", "QUASI_XML", "SECURE_XML"]`
    -   Environment Variable Override: `PYTHON_IRODSCLIENT_CONFIG__CONNECTIONS__XML_PARSER_DEFAULT`

For example, if `~/.python_irodsclient` contains the line :

```
connections.xml_parser_default        "QUASI_XML"
```

then the session below illustrates the effect of defining the
appropriate environment variable. Note the value stored in the variable
must be a valid input for `ast.literal_eval()`; that is, a
primitive Pythonic value - and quoted, for instance, if a string.

```bash
$ PYTHON_IRODSCLIENT_CONFIGURATION_PATH="" \
  PYTHON_IRODSCLIENT_CONFIG__CONNECTIONS__XML_PARSER_DEFAULT="'SECURE_XML'" \
  python -c "import irods.message, irods.client_configuration as c; print (irods.message.default_XML_parser())"
XML_Parser_Type.SECURE_XML
$ PYTHON_IRODSCLIENT_CONFIGURATION_PATH="" \
  python -c "import irods.message, irods.client_configuration as c; print (irods.message.default_XML_parser())"
XML_Parser_Type.QUASI_XML
```

Computing and Retrieving Checksums
----------------------------------

Each data object may be associated with a checksum by calling `chksum()`
on the object in question. Various behaviors can be elicited by passing
in combinations of keywords (for a description of which, please consult
the [header documentation](https://github.com/irods/irods/blob/4-3-stable/lib/api/include/irods/dataObjChksum.h).)

As with most other iRODS APIs, it is straightforward to specify keywords
by adding them to an options dictionary:

```python
>>> data_object_1.chksum() # - computes the checksum if already in the catalog, otherwise computes and stores it
...                        # (i.e. default behavior with no keywords passed in.)
>>> from irods.manager.data_object_manager import Server_Checksum_Warning
>>> import irods.keywords as kw
>>> opts = { kw.VERIFY_CHKSUM_KW:'' }
>>> try:
...     data_object_2.chksum( **opts ) # - Uses verification option. (Does not create or save a checksum in the catalog).
...     # or:
...     opts[ kw.NO_COMPUTE_KW ] = ''
...     data_object_2.chksum( **opts ) # - Uses both verification and no-compute options. (Like `ichksum -K --no-compute`)
... except Server_Checksum_Warning:
...     print('some checksums are missing or wrong')
```

Additionally, if a freshly created `irods.message.RErrorStack` instance is
given, information can be returned and read by the client:

```python
>>> from irods.message import RErrorStack
>>> r_err_stk = RErrorStack()
>>> warn = None
>>> try:   # Here, data_obj has one replica, not yet checksummed.
...     data_obj.chksum( r_error = r_err_stk , **{kw.VERIFY_CHKSUM_KW:''} )
... except Server_Checksum_Warning as exc:
...     warn = exc
>>> print(r_err_stk)
[RError<message = u'WARNING: No checksum available for replica [0].', status = -862000 CAT_NO_CHECKSUM_FOR_REPLICA>]
```

Working with metadata
---------------------

Showing the Attribute-Value-Units (AVUs) on an object with no metadata attached shows an empty list:

```python
>>> from irods.meta import iRODSMeta
>>> obj = session.data_objects.get("/tempZone/home/rods/test1")
>>> print(obj.metadata.items())
[]
```

Adding multiple AVUs with the same name field:

```python
>>> obj.metadata.add('key1', 'value1', 'units1')
>>> obj.metadata.add('key1', 'value2')
>>> obj.metadata.add('key2', 'value3')
>>> obj.metadata.add('key2', 'value4')
>>> print(obj.metadata.items())
[<iRODSMeta 13182 key1 value1 units1>, <iRODSMeta 13185 key2 value4 None>,
<iRODSMeta 13183 key1 value2 None>, <iRODSMeta 13184 key2 value3 None>]
```

We can also use Python's item indexing syntax to perform the equivalent
of an "imeta set \...", e.g. overwriting all AVUs with a name field
of "key2" in a single update:

```python
>>> new_meta = iRODSMeta('key2','value5','units2')
>>> obj.metadata\[new_meta.name\] = new_meta
>>> print(obj.metadata.items())
[<iRODSMeta 13182 key1 value1 units1>, <iRODSMeta 13183 key1 value2 None>,
<iRODSMeta 13186 key2 value5 units2>]
```

With only one AVU on the object with a name of "key2", *get_one*
is assured of not throwing an exception:

```python
>>> print(obj.metadata.get_one('key2'))
<iRODSMeta 13186 key2 value5 units2>
```

However, the same is not true of "key1":

```python
>>> print(obj.metadata.get_one('key1'))
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/[...]/python-irodsclient/irods/meta.py", line 41, in get_one
    raise KeyError
KeyError
```

Finally, to remove a specific AVU from an object:

```python
>>> obj.metadata.remove('key1', 'value1', 'units1')
>>> print(obj.metadata.items())
[<iRODSMeta 13186 key2 value5 units2>, <iRODSMeta 13183 key1 value2 None>]
```

Alternately, this form of the `remove()` method can also be useful:

```python
>>> for avu in obj.metadata.items():
...    obj.metadata.remove(avu)
>>> print(obj.metadata.items())
[]
```

If we intended on deleting the data object anyway, we could have just
done this instead:

```
>>> obj.unlink(force=True)
```

But notice that the force option is important, since a data object in
the trash may still have AVUs attached.

At the end of a long session of AVU add/manipulate/delete operations,
one should make sure to delete all unused AVUs. We can in fact use any
`*Meta` data model in the queries below, since unattached AVUs are
not aware of the (type of) catalog object they once annotated:

```python
>>> from irods.models import (DataObjectMeta, ResourceMeta)
>>> len(list( session.query(ResourceMeta) ))
4
>>> from irods.test.helpers import remove_unused_metadata
>>> remove_unused_metadata(session)
>>> len(list( session.query(ResourceMeta) ))
0
```

When altering a fetched iRODSMeta, we must copy it first to avoid
errors, due to the fact the reference is cached by the iRODS object
reference. A shallow copy is sufficient:

```python
>>> meta = album.metadata.items()[0]
>>> meta.units
'quid'
>>> import copy; meta = copy.copy(meta); meta.units = 'pounds sterling'
>>> album.metadata[ meta.name ] = meta
```

Since v1.1.4, `set()` can be used instead:

```python
>>> album.metadata.set( meta )
```

In versions of iRODS 4.2.12 and later, we can also do:

```python
>>> album.metadata.set( meta, \*\*{kw.ADMIN_KW: ''} )
```

or even:

```python
>>> album.metadata(admin = True)\[meta.name\] = meta
```

Since v1.1.5, the "timestamps" keyword is provided to enable the loading
of create and modify timestamps for every AVU returned from the server:

```python
>>> avus = album.metadata(timestamps = True).items()
>>> avus[0].create_time
datetime.datetime(2022, 9, 19, 15, 26, 7)
```

Atomic operations on metadata
-----------------------------

Since iRODS 4.2.8, the atomic metadata API
allows a group of metadata add and remove operations to be performed
transactionally, within a single call to the server. This capability is available
since PRC v0.8.6.

For example, if 'obj' is a handle to an object in the iRODS
catalog (whether a data object, collection, user, or storage resource),
we can send an arbitrary number of AVUOperation instances to be executed
together as one indivisible operation on that object:

```python
>>> from irods.meta import iRODSMeta, AVUOperation
>>> obj.metadata.apply_atomic_operations( AVUOperation(operation='remove', avu=iRODSMeta('a1','v1','these_units')),
...                                       AVUOperation(operation='add', avu=iRODSMeta('a2','v2','those_units')),
...                                       AVUOperation(operation='remove', avu=iRODSMeta('a3','v3')) \# , ...
... )
```

The list of operations are applied in the order given, so that a
"remove" followed by an "add" of the same AVU is, in effect, a
metadata "set" operation. Also note that a "remove" operation will
be ignored if the AVU value given does not exist on the target object at
that point in the sequence of operations.

We can also source from a pre-built list of AVUOperations using
Python's `f(*args_list)` syntax. For example, this
function uses the atomic metadata API to very quickly remove all AVUs
from an object:

```python
>>> def remove_all_avus( Object ):
...     avus_on_Object = Object.metadata.items()
...     Object.metadata.apply_atomic_operations( *[AVUOperation(operation='remove', avu=i) for i in avus_on_Object] )
```

Extracting JSON encoded server information in case of error
-----------------------------------------------------------

Some server APIs, including atomic metadata and replica truncation, can fail for various reasons and generate an
exception.  In these cases the message object returned from the server is made available in the 'server_msg' attribute
of the iRODSException object.

This enables an approach like the following, which logs server information possibly underlying the error that was evoked:

```python
    try:
        Object.metadata.apply_atomic_operations( ops )
        # or:
        DataObject.replica_truncate( size )
    except iRODSException as exc:
        log.error('Server API call failure. Traceback = %r ; iRODS Server info = %r',
            traceback.extract_tb(sys.exc_info()[2]),
            exc.server_msg.get_json_encoded_struct())
```

For `DataObject.replica_truncate(...)`, note that `exc.server_msg.get_json_encoded_struct()` can be used in the exception-handling
code path to retrieve the same information that would have been routinely returned from the truncate call itself, had it actually
completed without error.

Special Characters
------------------

iRODS supports Unicode characters into collection and
data object names. However, certain non-printable ASCII characters, in addition to
the backquote character, have historically presented problems
- especially for clients using the iRODS human readable XML protocol.
Consider this small, contrived application:

```python
    from irods.helpers import make_session

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
            create_notes( session, "lucky\1.dat", content = u'test' )
        except:
            pass

        # Example 2 (Ref. issue: irods/irods #4132, fixed for 4.2.9 release of iRODS)
        print(
            create_notes(session, "Alice`s diary").name  # The difference in the printed name is subtle, as
                                                         # "`" is transformed to "'" in iRODS pre-4.2.9
        )
```

This creates two data objects, but with less than optimal success. The
first example object is created but receives no content because an
exception is thrown trying to query its name after creation. In the
second example, for iRODS 4.2.8 and before, a deficiency in packStruct
XML protocol causes the backtick to be read back as an apostrophe, which
could create problems manipulating or deleting the object later.

Since v1.1.0, both problems can be mitigated by switching in the
QUASI_XML parser for the default one:

```
    from irods.message import (XML_Parser_Type, ET)
    ET( XML_Parser_Type.QUASI_XML,
        server_version = session.server_version
    )
```

The server_version parameter can be used independently to change the
current thread's choice of entities during QUASI_XML transactions with the server.
(This is only a concern when interacting with servers before iRODS 4.2.9.)

```
    ET(server_version = (4,2,8))
```

Two dedicated environment variables may also be used to customize the
Python client's XML parsing behavior via the setting of global defaults
during start-up.

For example, we can set the default parser to QUASI_XML, optimized for
use with version 4.2.8 of the iRODS server, in the following manner:

```
    Bash-Shell> export PYTHON_IRODSCLIENT_DEFAULT_XML=QUASI_XML PYTHON_IRODSCLIENT_QUASI_XML_SERVER_VERSION=4,2,8
```

Other alternatives for PYTHON_IRODSCLIENT_DEFAULT_XML are
"STANDARD_XML" and "SECURE_XML". These two latter options denote
use of the xml.etree and defusedxml modules, respectively.

Only the choice of "QUASI_XML" is affected by the specification of a
particular server version.

These global defaults, once set, may be overridden on
a per-thread basis using `ET(parser_type, server_version)`.

The current thread's XML parser can always be reverted to the global default by the
explicit use of `ET(None)`.  However, when frequently switching back and forth between
parsers, it may be more convenient to use the `xml_mode` context manager:

```
    # ... Interactions with the server now use the default XML parser.

    from irods.helpers import xml_mode
    with xml_mode('QUASI_XML'):
        # ... Interactions with the server, in the current thread, temporarily use QUASI_XML

    # ... We have now returned to using the default XML parser.
```

Application Cleanup
-------------------

Using the `irods.at_client_exit` module, we may register user-defined functions to be executed at or around the
time when the Python iRODS Client is engaged in object teardown (also called "cleanup") operations.
This is analogous to Python's [atexit module](https://docs.python.org/3/library/atexit.html#module-atexit),
except that here we have the extra resolution to specify that a function or callable object be expressly before,
or expressly after, aforementioned object teardown stage:

```python
    from irods import at_client_exit
    at_client_exit.register_for_execution_after_prc_cleanup(lambda: print("PRC cleanup has completed."))
    at_client_exit.register_for_execution_before_prc_cleanup(lambda: print("PRC cleanup is about to start."))
```

A function normally cannot be registered multiple times to run in the same stage, but we may overcome this limitation
(and, optionally, arguments set for the invocation) by wrapping the same function into two different callable objects:

```python
    def print_exit_message(n):
        print(f"Called just after PRC cleanup - iteration {n}")

    for n_iter in (1,2):
        at_client_exit.register_for_execution_after_prc_cleanup(
            at_client_exit.unique_function_invocation(print_exit_message, tup_args = (n_iter,))
            )
```

The output of the above, upon script exit, will be:

```
Called just after PRC cleanup - iteration 2
Called just after PRC cleanup - iteration 1
```

which may be reversed from the order that one might expect.  This is because -- similarly as with Python atexit module, and
consistently with the teardown of higher abstractions before lower ones -- functions _registered_ later within a given cleanup
stage will actually be _executed_ sooner (i.e. in "LIFO" order).

Rule Execution
--------------

The following example shows how to execute an iRODS rule from the Python iRODS client.

A rule file `native1.r` contains a rule in the native iRODS Rule Language:

```
    main() {
        writeLine("*stream",
                  *X ++ " squared is " ++ str(double(*X)^2) )
    }

    INPUT *X="3", *stream="serverLog"
    OUTPUT null
```

The following Python client code will run the rule and produce the
appropriate output in the iRODS server log:

```
    r = irods.rule.Rule( session, rule_file = 'native1.r')
    r.execute()
```

Since v1.1.1, not only can we target a specific rule engine
instance by name (which is useful when more than one is present), but we
can also use a file-like object for the `rule_file`
parameter:

```
    Rule( session, rule_file = io.StringIO(u'''mainRule() { anotherRule(*x); writeLine('stdout',*x) }\n'''
                                           u'''anotherRule(*OUT) {*OUT='hello world!'}\n\n'''
                                           u'''OUTPUT ruleExecOut\n'''),
          instance_name = 'irods_rule_engine_plugin-irods_rule_language-instance' )
```

If we wanted to change the `native1.r` rule
code print to `stdout`, we could set the `INPUT`
parameter, `*stream`, using the Rule constructor's
`params` keyword argument. Similarly, we can change the
`OUTPUT` parameter from `null` to
`ruleExecOut`, to accommodate the output stream, via the
`output` argument:

```
    r = irods.rule.Rule( session, rule_file = 'native1.r',
               instance_name = 'irods_rule_engine_plugin-irods_rule_language-instance',
               params={'*stream':'"stdout"'} , output = 'ruleExecOut' )
    output = r.execute( )
    if output and len(output.MsParam_PI):
        buf = output.MsParam_PI[0].inOutStruct.stdoutBuf.buf
        if buf: print(buf.rstrip(b'\0').decode('utf8'))
```

To deal with errors resulting from rule execution failure, two
approaches can be taken. Suppose we have defined this in the
`/etc/irods/core.re` rule base:

```
    rule_that_fails_with_error_code(*x) {
      *y = (if (*x!="") then int(*x) else 0)
    # if (SOME_PROCEDURE_GOES_WRONG) {
        if (*y < 0) { failmsg(*y,"-- my error message --"); }  #-> throws an error code of int(*x) in REPF
        else { fail(); }                                       #-> throws FAIL_ACTION_ENCOUNTERED_ERR in REPF
    # }
    }
```

We can run the rule thus:

```python
>>> Rule( session, body='rule_that_fails_with_error_code(""), instance_name = 'irods_rule_engine_plugin-irods_rule_language-instance',
...     ).execute( r_error = (r_errs:= irods.message.RErrorStack()) )
```

Where we've used the Python 3.8+ "walrus operator" for brevity. The
error will automatically be caught and translated to a returned-error
stack:

```python
>>> pprint.pprint([vars(r) for r in r_errs])
[{'raw_msg_': 'DEBUG: fail action encountered\n'
              'line 14, col 15, rule base core\n'
              '        else { fail(); }\n'
              '               ^\n'
              '\n',
  'status_': -1220000}]
```

Note, if a stringized negative integer is given , i.e. as a special fail
code to be thrown within the rule, we must add this code into the `acceptable_errors`
parameter to have this automatically caught as well:

```python
>>> Rule( session, body='rule_that_fails_with_error_code("-2")',instance_name = 'irods_rule_engine_plugin-irods_rule_language-instance'
...     ).execute( acceptable_errors = ( FAIL_ACTION_ENCOUNTERED_ERR, -2),
...                r_error = (r_errs := irods.message.RErrorStack()) )
```

Because the rule is written to emit a custom error message via `failmsg()`,
the resulting r_error stack will now include that custom
error message as a substring:

```python
>>> pprint.pprint([vars(r) for r in r_errs])
[{'raw_msg_': 'DEBUG: -- my error message --\n'
              'line 21, col 20, rule base core\n'
              '      if (*y < 0) { failmsg(*y,"-- my error message --"); }  '
              '#-> throws an error code of int(*x) in REPF\n'
              '                    ^\n'
              '\n',
  'status_': -1220000}]
```

Alternatively, or in combination with the automatic catching of errors,
we may also catch errors as exceptions on the client side. For example,
if the Python rule engine is configured, and the following rule is
placed in `/etc/irods/core.py`:

```python
def python_rule(rule_args, callback, rei):
#   if some operation fails():
        raise RuntimeError
```

we can trap the error thus:

```python
try:
    Rule( session, body = 'python_rule', instance_name = 'irods_rule_engine_plugin-python-instance' ).execute()
except irods.exception.RULE_ENGINE_ERROR:
    print('Rule execution failed!')
    exit(1)
print('Rule execution succeeded!')
```

As fail actions from native rules are not thrown by default (refer to
the help text for `Rule.execute`), if we anticipate these
and prefer to catch them as exceptions, we can do it this way:

```python
try:
    Rule( session, body = 'python_rule', instance_name = 'irods_rule_engine_plugin-python-instance'
         ).execute( acceptable_errors = () )
except (irods.exception.RULE_ENGINE_ERROR,
        irods.exception.FAIL_ACTION_ENCOUNTERED_ERR) as e:
    print('Rule execution failed!')
    exit(1)
print('Rule execution succeeded!')
```

Finally, keep in mind that rule code submitted through an
`irods.rule.Rule` object is processed by the
exec_rule_text function in the targeted plugin instance in the server.
This may be a
limitation for plugins not equipped to handle rule code in this way. In
a sort of middle-ground case, the iRODS Python Rule Engine Plugin is not
currently able to handle simple rule calls and the manipulation of iRODS
core primitives (like simple parameter passing and variable expansion')
as flexibly as the iRODS Rule Language.

Also, core.py rules may only be run directly by a rodsadmin, currently.
[See this issue for discussion](https://github.com/irods/irods_rule_engine_plugin_python/issues/105).


GenQuery1 Queries
-----------------

A session object's `query` method accepts a list of columns and models to be included in any returned rows.

Below, as an example, the DataObject and Collection tables are joined for the purposes of executing an
iRODS general query (or "GenQuery") for data objects, with the results containing all available columns from 
the Collection model and a limited set of DataObject columns.

```python
>>> import os
>>> from irods.session import iRODSSession
>>> from irods.models import Collection, DataObject
>>>
>>> env_file = os.path.expanduser('~/.irods/irods_environment.json')
>>> with iRODSSession(irods_env_file=env_file) as session:
...     query = session.query(Collection, DataObject.id, DataObject.name, DataObject.size)
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
```

Columns can be excluded from the results by negating them.  Order is significant:

```python
>>> query = session.query(Collection, DataObject, -DataObject.map_id, -DataObject.status, -Collection.map_id)
```

Query using other models:

```python
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
```

Since v0.8.3, the 'In()' operator is available:

```python
>>> from irods.models import Resource
>>> from irods.column import In
>>> [ resc[Resource.id]for resc in session.query(Resource).filter(In(Resource.name, ['thisResc','thatResc'])) ]
[10037,10038]
```

Query with aggregation(min, max, sum, avg, count):

```python
>>> with iRODSSession(irods_env_file=env_file) as session:
...     query = session.query(DataObject.owner_name).count(DataObject.id).sum(DataObject.size)
...     print(next(query.get_results()))
{<irods.column.Column 411 D_OWNER_NAME>: 'rods', <irods.column.Column 407 DATA_SIZE>: 62262, <irods.column.Column 401 D_DATA_ID>: 14}
```

In this case since we are expecting only one row we can directly call
`query.execute()`:

```python
>>> with iRODSSession(irods_env_file=env_file) as session:
...     query = session.query(DataObject.owner_name).count(DataObject.id).sum(DataObject.size)
...     print(query.execute())
+--------------+-----------+-----------+
| D_OWNER_NAME | D_DATA_ID | DATA_SIZE |
+--------------+-----------+-----------+
| rods         | 14        | 62262     |
+--------------+-----------+-----------+
```

For a case-insensitive query, add a `case_sensitive=False`
parameter to the query:

```python
>>> with iRODSSession(irods_env_file=env_file) as session:
...     query = session.query(DataObject.name, case_sensitive=False).filter(Like(DataObject.name, "%oBjEcT"))
...     print(query.all())
+---------------------+
| DATA_NAME           |
+---------------------+
| caseSENSITIVEobject |
+---------------------+
```

If the user desires a smaller paging size, this can be accomplished by changing
the `genquery1.irods_query_limit` configuration setting.  This directly changes
the `irods.query.IRODS_QUERY_LIMIT` value and therefore affects Query objects'
`all` and `get_batches` methods.

Note, however, that expressions such as `list(Query(...))` and `(row for row in
Query)` are not affected by this setting.

The setting may be given any positive integer value.  Attempting to set it to
zero or a negative number will not affect the value of `IRODS_QUERY_LIMIT` but will
raise a `ConfigurationValueError` if done in the course of a running iRODS
client application.  Importantly, if the invalid setting is attempted by a loading
configuration, the otherwise fatal error could be absorbed into a warning-level log action,
depending on the value of the `PYTHON_IRODSCLIENT_CONFIGURATION_LOAD_ERRORS_FATAL`
environment variable.  See: [Python iRODS Client Settings File](#python-irods-client-settings-file).

A copy of the original value of `IRODS_QUERY_LIMIT` (before overriding values are loaded from the
configuration) is stored within `irods.query.cached_values.IRODS_QUERY_LIMIT`.

Specific Queries
----------------

```python
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
```

Recherché Queries
-----------------

In some cases you might like to use a GenQuery operator not directly
offered by this Python library, or even combine query filters in ways
GenQuery may not directly support.

As an example, the code below finds metadata value fields
lexicographically outside the range of decimal integers, while also
requiring that the data objects to which they are attached do not reside
in the trash.

```python
>>> search_tuple = (DataObject.name , Collection.name ,
...                 DataObjectMeta.name , DataObjectMeta.value)

>>> # "not like" : direct instantiation of Criterion (operator in literal string)
>>> not_in_trash = Criterion ('not like', Collection.name , '%/trash/%')

>>> # "not between"( column, X, Y) := column < X OR column > Y ("OR" done via chained iterators)
>>> res1 = session.query (* search_tuple).filter(not_in_trash).filter(DataObjectMeta.value < '0')
>>> res2 = session.query (* search_tuple).filter(not_in_trash).filter(DataObjectMeta.value > '9' * 9999 )

>>> chained_results = itertools.chain ( res1.get_results(), res2.get_results() )
>>> pprint( list( chained_results ) )
```

Instantiating iRODS objects from query results
----------------------------------------------

The General query works well for getting information out of the ICAT if
all we're interested in is information representable with primitive
types (i.e. object names, paths, and ID's, as strings or integers). But
Python's object orientation also allows us to create object references
to mirror the persistent entities (instances of *Collection*,
*DataObject*, *User*, or *Resource*, etc.) inhabiting the ICAT.

**Background:**

Certain iRODS object types can be instantiated easily
using the session object's custom type managers, particularly if some
parameter (often just the name or path) of the object is already known:

```python
>>> type(session.users)
<class 'irods.manager.user_manager.UserManager'>
>>> u = session.users.get('rods')
>>> u.id
10003
```

Type managers are good for specific operations, including object
creation and removal:

```python
>>> session.collections.create('/tempZone/home/rods/subColln')
>>> session.collections.remove('/tempZone/home/rods/subColln')
>>> session.data_objects.create('/tempZone/home/rods/dataObj')
>>> session.data_objects.unlink('/tempZone/home/rods/dataObj')
```

When we retrieve a reference to an existing collection using *get* :

```python
>>> c = session.collections.get('/tempZone/home/rods')
>>> c
<iRODSCollection 10011 rods>
```

we have, in that variable *c*, a reference to an iRODS *Collection*
object whose properties provide useful information:

```python
>>> [ x for x in dir(c) if not x.startswith('__') ]
['_meta', 'data_objects', 'id', 'manager', 'metadata', 'move', 'name', 'path', 'remove', 'subcollections', 'unregister', 'walk']
>>> c.name
'rods'
>>> c.path
'/tempZone/home/rods'
>>> c.data_objects
[<iRODSDataObject 10019 test1>]
>>> c.metadata.items()
[ <... list of AVUs attached to Collection c ... > ]
```

or whose methods can do useful things:

```python
>>> for sub_coll in c.walk(): print('---'); pprint( sub_coll )
[ ...< series of Python data structures giving the complete tree structure below collection 'c'> ...]
```

This approach of finding objects by name, or via their relations with
other objects (ie "contained by", or in the case of metadata,
"attached to"), is helpful if we know something about the location or
identity of what we're searching for, but we don't always have that
kind of a-priori knowledge.

So, although we can (as seen in the last example) walk an
*iRODSCollection* recursively to discover all subordinate collections
and their data objects, this approach will not always be best for a
given type of application or data discovery, especially in more advanced
use cases.

**A Different Approach:**

For the PRC to be sufficiently powerful for general use, we'll often need at least:

-   general queries, and
-   the capabilities afforded by the PRC's object-relational mapping.

Suppose, for example, we wish to enumerate all collections in the iRODS
catalog.

Again, the object managers are the answer, but they are now invoked
using a different scheme:

```python
>>> from irods.collection import iRODSCollection; from irods.models import Collection
>>> all_collns = [ iRODSCollection(session.collections, result) for result in session.query(Collection) ]
```

From there, we have the ability to do useful work, or filtering based on
the results of the enumeration. And, because *all_collns* is an
iterable of true objects, we can either use Python's list
comprehensions or execute more catalog queries to achieve further aims.

Note that, for similar system-wide queries of Data Objects (which, as it
happens, are inextricably joined to their parent Collection objects), a
bit more finesse is required. Let us query, for example, to find all
data objects in a particular zone with an AVU that matches the following
condition:

```
    META_DATA_ATTR_NAME = "irods::alert_time" and META_DATA_ATTR_VALUE like '+0%'
```

```python
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
```

In the above loop we have used a helper function, *get_collection*, to
minimize the number of hits to the object catalog. Otherwise, me might
find within a typical application that some Collection objects are being
queried at a high rate of redundancy. *get_collection* can be
implemented thusly:

```python
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
```

Once instantiated, of course, any *iRODSDataObject*'s data to which we
have access permissions is available via its open() method.

As stated, this type of object discovery requires some extra study and
effort, but the ability to search arbitrary iRODS zones (to which we are
federated and have the user permissions) is powerful indeed.


GenQuery2 Queries
-----------------

GenQuery2 is a successor to the regular GenQuery interface. It is available
by default on iRODS 4.3.2 and higher. GenQuery2 currently has an experimental status,
and is subject to change.

Queries can be executed using the `genquery2` function and passing a single querystring.  All parsing is done on the server.

For example:

```
>>> session.genquery2("SELECT COLL_NAME WHERE COLL_NAME = '/tempZone/home' OR COLL_NAME LIKE '%/genquery2_dummy_doesnotexist'")
[['/tempZone/home']]
```

Alternatively, create a GenQuery2 object and use it to execute queries. For example:

```
>>> q = session.genquery2_object()
>>> q.execute("SELECT COLL_NAME WHERE COLL_NAME = '/tempZone/home' OR COLL_NAME LIKE '%/genquery2_dummy_doesnotexist'", zone="tempZone")
[['/tempZone/home']]
```

GenQuery2 objects also support retrieving only the SQL generated by a GenQuery2 query using the
`get_sql` function and retrieving all available column mappings using the `get_column_mappings` function.


Tickets
-------

The `irods.ticket.Ticket` class lets us issue "tickets"
which grant limited permissions for other users to access our own data
objects (or collections of data objects). As with the iticket client,
the access may be either "read" or "write". The recipient of the
ticket could be a rodsuser, or even an anonymous user.

Below is a demonstration of how to generate a new ticket for access to a
logical path - in this case, say a collection containing 1 or more data
objects. (We assume the creation of the granting_session and
receiving_session for the users respectively for the users providing
and consuming the ticket access.)

The user who wishes to provide an access may execute the following:

```python
>>> from irods.ticket import Ticket
>>> new_ticket = Ticket (granting_session)
>>> The_Ticket_String = new_ticket.issue('read', 
...     '/zone/home/my/collection_with_data_objects_for/somebody').string
```

at which point that ticket's unique string may be given to other users,
who can then apply the ticket to any existing session object in order to
gain access to the intended object(s):

```python
>>> from irods.models import Collection, DataObject
>>> ses = receiving_session
>>> Ticket(ses, The_Ticket_String).supply()
>>> c_result = ses.query(Collection).one()
>>> c = iRODSCollection( ses.collections, c_result)
>>> for dobj in (c.data_objects):
...     ses.data_objects.get( dobj.path, '/tmp/' + dobj.name ) # download objects
```

In this case, however, modification will not be allowed because the
ticket is for read only:

```python
>>> c.data_objects[0].open('w').write(  # raises
...     b'new content')                 #  CAT_NO_ACCESS_PERMISSION
```

In another example, we could generate a ticket that explicitly allows
'write' access on a specific data object, thus granting other users
the permissions to modify as well as read it:

```python
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
```

As with iticket, we may set a time limit on the availability of a
ticket, either as a timestamp or in seconds since the epoch:

```python
>>> t=Ticket(ses); s = t.string
vIOQ6qzrWWPO9X7
>>> t.issue('read','/some/path')
>>> t.modify('expire','2021-04-01.12:34:56')  # timestamp assumed as UTC
```

To check the results of the above, we could invoke this icommand
elsewhere in a shell prompt:

```
iticket ls vIOQ6qzrWWPO9X7
```

and the server should report back the same expiration timestamp.

And, if we are the issuer of a ticket, we may also query, filter on, and
extract information based on a ticket's attributes and catalog
relations:

```python
>>> from irods.models import TicketQuery
>>> delay = lambda secs: int( time.time() + secs + 1)
>>> Ticket(ses).issue('read','/path/to/data_object').modify(
                      'expire',delay(7*24*3600))             # lasts 1 week
>>> Q = ses.query (TicketQuery.Ticket, TicketQuery.DataObject).filter(
...                                                            TicketQuery.DataObject.name == 'data_object')
>>> print ([ _[TicketQuery.Ticket.expiry_ts] for _ in Q ])
['1636757427']
```

Tracking and manipulating replicas of Data Objects
--------------------------------------------------

Putting together the techniques we've seen so far, it's not hard to write client code to accomplish
useful, common tasks.  Suppose, for instance, that a data object contains replicas on a given resource
or resource hierarchy (the "source"), and we want those replicas "moved" to a second resource
(the "destination").  This can be done by combining the replicate and trim operations, as in the following
code excerpt.

We'll assume, for our current purposes, that all pre-existing replicas are good (ie. they have a
`status` attribute of `'1'`); and that the nodes in question are named `src` and `dest`,
with `src` being the root node of a resource hierarchy and `dest` just a simple storage node.

Then we can accomplish the replica "move" thus:

```python
  path = '/path/to/data/object'
  data = session.data_objects.get('/path/to/data/object')

  # Replicate the data object to the destination.

  data.replicate(**{kw.DEST_RESC_NAME_KW: 'dest'})

  # Find and trim replicas on the source resource hierarchy.

  replica_numbers = [r.number for r in d.replicas if r.resc_hier.startswith('src;')]
  for number in replica_numbers:
      session.data_objects.trim(path, **{kw.DATA_REPL_NUM:number, kw.COPIES_KW:1})
```

Users and Groups
----------------

iRODS tracks users and groups using two tables, R_USER_MAIN and
R_USER_GROUP. Under this database schema, all groups are also users:

```python
>>> from irods.models import User, Group
>>> from pprint import pprint
>>> pprint(list((x[User.id], x[User.name]) for x in session.query(User)))
[(10048, 'alice'),
 (10001, 'rodsadmin'),
 (13187, 'bobby'),
 (10045, 'collab'),
 (10003, 'rods'),
 (13193, 'empty'),
 (10002, 'public')]
```

But it's also worth noting that the User.type field will be
'rodsgroup' for any user ID that iRODS internally recognizes as a
"Group":

```python
>>> groups = session.query(User).filter( User.type == 'rodsgroup' )

>>> [x[User.name] for x in groups]
['collab', 'public', 'rodsadmin', 'empty']
```

Since we can instantiate iRODSGroup and iRODSUser objects directly from
the rows of a general query on the corresponding tables, it is also
straightforward to trace out the groups' memberships:

```python
>>> from irods.user import iRODSUser, iRODSGroup
>>> grp_usr_mapping = [ (iRODSGroup(session.groups, result), iRODSUser(session.users, result)) \
...                     for result in session.query(Group,User) ]
>>> pprint( [ (x,y) for x,y in grp_usr_mapping if x.id != y.id ] )
[(<iRODSGroup 10045 collab>, <iRODSUser 10048 alice rodsuser tempZone>),
 (<iRODSGroup 10001 rodsadmin>, <iRODSUser 10003 rods rodsadmin tempZone>),
 (<iRODSGroup 10002 public>, <iRODSUser 10003 rods rodsadmin tempZone>),
 (<iRODSGroup 10002 public>, <iRODSUser 10048 alice rodsuser tempZone>),
 (<iRODSGroup 10045 collab>, <iRODSUser 13187 bobby rodsuser tempZone>),
 (<iRODSGroup 10002 public>, <iRODSUser 13187 bobby rodsuser tempZone>)]
```

(Note that in general queries, fields cannot be compared to each other,
only to literal constants; thus the '!=' comparison in the Python list
comprehension.)

From the above, we can see that the group 'collab' (with user ID
10045) contains users 'bobby'(13187) and 'alice'(10048) but not
'rods'(10003), as the tuple (10045,10003) is not listed. Group
'rodsadmin'(10001) contains user 'rods'(10003) but no other users;
and group 'public'(10002) by default contains all canonical users
(those whose User.type is 'rodsadmin' or 'rodsuser'). The empty
group ('empty') has no users as members, so it doesn't show up in our
final list.

Group Administrator Capabilities
--------------------------------

Since v1.1.7, group administrator functions are available.

A groupadmin may invoke methods to create groups, and may add
users to, or remove them from, any group to which they themselves
belong:

```python
>>> session.groups.create('lab')
>>> session.groups.addmember('lab',session.username)  # allow self to administer group
>>> session.groups.addmember('lab','otheruser')
>>> session.groups.removemember('lab','otheruser')
```

A groupadmin may also create accounts for new users and
enable their logins by initializing a native password for them:

```python
>>> session.users.create_with_password('alice', password='change_me')
```

However, note that passwords may only be created for local users.

When an entry for some remote user must be made into the local zone's catalog, a
groupadmin may do the following:

```
>>> session.users.create_remote('alice', user_zone='other_zone')
```

iRODS Permissions (ACLs)
------------------------

The `iRODSAccess` class offers a convenient dictionary
interface mapping iRODS permission strings to the corresponding integer
codes:

```python
>>> from irods.access import iRODSAccess
>>> iRODSAccess.keys()
['null', 'read_metadata', 'read_object', 'create_metadata', 'modify_metadata', 'delete_metadata', 'create_object', 'modify_object', 'delete_object', 'own']
>>> WRITE = iRODSAccess.to_int('modify_object')
```

Armed with that, we can then query on all data objects with ACLs that
allow our user to write them:

```python
>>> from irods.models import (DataObject, User, DataAccess)
>>> data_objects_writable = list(session.query(DataObject, User, DataAccess).filter(User.name == session.username,  DataAccess.type >= WRITE))
```

Finally, we can also access the list of permissions available through a
given session object via the `available_permissions`
property. Note that (in keeping with changes in iRODS 4.3+)
the permissions list will be longer, as appropriate, for session objects
connected to the more recent servers; and also that the embedded spaces
in some 4.2 permission strings are replaced by underscores in 4.3
and later.

```python
>>> session.server_version
(4, 2, 11)
>>> session.available_permissions.items()
[('null', 1000), ('read object', 1050), ('modify object', 1120), ('own', 1200)]
```

Getting and setting permissions
-------------------------------

We can find the ID's of all the collections writable (i.e. having
a "modify" ACL) by, but not owned by, alice (or even alice\#otherZone):

```python
>>> from irods.models import Collection,CollectionAccess,CollectionUser,User
>>> from irods.column import Like
>>> q = session.query (Collection,CollectionAccess).filter(
...                                 CollectionUser.name == 'alice',  # User.zone == 'otherZone', # zone optional
...                                 Like(CollectionAccess.name, 'modify%') ) #defaults to current zone
```

If we then want to downgrade those permissions to read-only, we can do
the following:

```python
>>> from irods.access import iRODSAccess
>>> for c in q:
...     session.acls.set( iRODSAccess('read', c[Collection.name], 'alice', # 'otherZone' # zone optional
...     ))
```

A call to `session.acls.get(c)` -- with `c`
being the result of
`sessions.collections.get(c[Collection.name])` -- would
then verify the desired change had taken place (as well as list all ACLs
stored in the catalog for that collection).

The older access manager,
`<session>.permissions`, produced inconsistent results when
the `get()` method was invoked with the parameter
`report_raw_acls` set (or defaulting) to
`False`. Specifically, collections would exhibit the
"non-raw-ACL" behavior of reporting individual member users'
permissions as a by-product of group ACLs, whereas data objects would
not.

Since v1.1.6, this inconsistency is corrected by
`<session>.acls` which acts almost identically
to `<session>.permissions`, except that the
`<session>.acls.get(...)` method does not accept the
`report_raw_acls` parameter. When we need to detect users'
permissions independent of their access to an object via group
membership, this can be achieved with another query.

`<session>.permissions` was therefore removed in v2.0.0
in favor of `<session>.acls`.

Quotas (v2.0.0)
---------------

Quotas may be set for a group:

```python
session.groups.set_quota('my_group', 50000, resource = 'my_limited_resource')
```

or per user, prior to iRODS 4.3.0:

```python
session.users.set_quota('alice', 100000)
```

The default for the resource parameter is "total", denoting a general
quota usage not bound to a particular resource.

The Quota model is also available for queries. So, to determine the
space remaining for a certain group on a given resource:

```python
from irods.models import Quota
session.groups.calculate_usage()
group, resource = ['my_group', 'my_limited_resource']
space_left_in_bytes = list(session.query(Quota.over).filter(Quota.user_id == session.groups.get(group).id,
                                                            Quota.resc_id == session.resources.get(resource).id))[0][Quota.over] * -1
```

And, to remove all quotas for a given group, one might (as a rodsadmin)
do the following:

```python
from irods.models import Resource, Quota
resc_map = dict([(x[Resource.id],x[Resource.name]) for x in sess.query(Resource)] + [(0,'total')])
group = sess.groups.get('my_group')
for quota in sess.query(Quota).filter(Quota.user_id == group.id):
    sess.groups.remove_quota(group.name, resource = resc_map[quota.resc_id])
```

Managing users
--------------

You can create a user in the current zone (with an optional auth_str):

```python
>>> session.users.create('user', 'rodsuser', 'MyZone', auth_str)
```

If you want to create a user from a federated zone, use:

```python
>>> session.users.create('user', 'rodsuser', 'OtherZone', auth_str)
```

Showing client hints
--------------------

You can get a list of available microservices, rules, etc. using the `client_hints`
attribute of the session.

```python
>>> session.client_hints
```

Code Samples and Tests
----------------------

Additional code samples are available in the [test
directory](https://github.com/irods/python-irodsclient/tree/main/irods/test)

Testing
=======

Setting up and running tests
----------------------------

The Python iRODS Client comes with its own suite of tests. Some amount
of setting up may be necessary first:

1.  Use `iinit` to specify the iRODS client environment.
    For best results, point the client at a server running on the local
    host.
2.  Install the python-irodsclient along with the
    `unittest unittest_xml_reporting` module or the older
    `xmlrunner` equivalent.
    -   `pip install ./path-to-python-irodsclient-repo[tests]`
        (when using a local Git repo); or,
    -   `pip install python-irodsclient[tests]'>=1.1.1'`
        (when installing directly from PyPI).
3.  Follow further instructions in the [test
    README file](https://github.com/irods/python-irodsclient/tree/main/irods/test/README.rst)

Testing S3 parallel transfer
----------------------------

System requirements:

    - Ubuntu 18 user with Docker installed.
    - Local instance of iRODS server running.
    - Logged in sudo privileges.

Run a MinIO service:

```
$ docker run -d -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ":9001"
```

Set up a bucket `s3://irods` under MinIO:

```
$ pip install awscli

$ aws configure
AWS Access Key ID [None]: minioadmin
AWS Secret Access Key [None]: minioadmin
Default region name [None]:
Default output format [None]:

$ aws --endpoint-url http://127.0.0.1:9000 s3 mb s3://irods
```

Set up s3 credentials for the iRODS s3 storage resource:

```
$ sudo su - irods -c "/bin/echo -e 'minioadmin\nminioadmin' >/var/lib/irods/s3-credentials"
$ sudo chown 600 /var/lib/irods/s3-credentials
```

Create the s3 storage resource:

```
$ sudo apt install irods-resource-plugin-s3
```

As the 'irods' service account user:

```
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

$ python -c"\
from irods.helpers import make_session
import irods.keywords as kw
with make_session() as sess:
    sess.data_objects.put( 'largefile',
                           '/tempZone/home/rods/largeFile1',
                           **{kw.DEST_RESC_NAME_KW:'s3resc'} )
    sess.data_objects.get( '/tempZone/home/rods/largeFile1',
                           '/tmp/largefile')"
```
