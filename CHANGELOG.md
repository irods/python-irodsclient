# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project **only** adheres to the following _(as defined at [Semantic Versioning](https://semver.org/spec/v2.0.0.html))_:

> Given a version number MAJOR.MINOR.PATCH, increment the:
> 
> - MAJOR version when you make incompatible API changes
> - MINOR version when you add functionality in a backward compatible manner
> - PATCH version when you make backward compatible bug fixes

## [v3.1.1] - 2025-06-09

This patch release resolves bugs related to connections, `ips` tracking, and dependencies.

### Changed

- Log authentication messages at DEBUG level (#706).
- Remove dependency on test module (#735).

### Fixed

- Add missing import to connection.py (#5).
- Allow `put` and `create` of data object to raise an error on overwrite (#132, #322).
- Do not create local file when download of nonexistent data object fails (#681, #714).
- Trap exception in connection finalizer (#691).
- Fix imports for `make_session` in README examples (#710).
- Remove semicolon from `<option>` tag in `StartupPack` (#730).

### Added

- Add exception class for `HIERARCHY_ERROR` (#717).
- Add exception class for `SYS_SOCK_READ_TIMEDOUT` (#718).

## [v3.1.0] - 2025-03-21

This release includes a full port of the iRODS 4.3 authentication framework with working implementations for the native and pam_password authentication schemes.

It also removes support for Python versions earlier than 3.9.

### Changed

- Implement iRODS 4.3 authentication flow for native and pam_password authentication schemes (#499).
- Replace deprecated use of hyphen in description file property name (#684).
- Change server version compatibility to iRODS 4.3.4 (#694).

### Removed

- Remove support for Python 3.8 and earlier (#553).

### Fixed

- Make computation of .irodsA file path independent of irods_environment.json file path (#686).
- Adjust strings in tests to avoid SyntaxWarning messages (#687).

### Added

- Allow retrieval of connected server version without having to authenticate first (#688).

## [v3.0.0] - 2024-12-19

This major release primarily focuses on the removal of Python 2 compatibility. With that comes improvements for PAM authentication and facilities to help with cleaning up resources on program shutdown. 

### Changed

- Remove Python 2 compatibility (#480).
- Format codebase using Black formatter (#615).
- Expose keyword parameter for controlling whether the .irodsA file is to be overwritten (#635).
- Check environment variable is defined before use, to avoid SyntaxError (#641).
- Improve documentation (#651, #654).
- Replace use of `utcfromtimestamp` and `utcnow` (#670).

### Fixed

- Correct faulty GenQuery1 column mappings (#642, #643).
- Escape special characters in passwords for PAM authentication (#649, #650).
- Catch `ENOTCONN` error from `socket.shutdown()` on BSD/MacOS (#657).
- Remove call to initialize log facilities on import of irods module (#660).

### Added

- Provide mechanism for registering deterministic execution of cleanup functions on program shutdown (#614).
- Add `SYS_LIBRARY_ERROR` to irods.exception module (#668).

## [v2.2.0] - 2024-10-14

### Changed

- Bump server compatibility to iRODS 4.3.3 (#3).
- Limit maximum value for connection timeouts (#623).
- Disable client redirection to resource, by default (#626, #627).

### Fixed

- Adjust use of imported symbols from module for testing (#613).
- Modify the correct object in session.clone() for `ticket_applied` attribute (#619).
- Correct ticket expire example in README (#630).

### Added

- Attach server response to exception as `server_msg` attribute (#606).
- Add `CAT_TICKET_USES_EXCEEDED` to irods.exception module (#632).

## [v2.1.0] - 2024-08-13

- [#3] v2.1.0 and update changelog [Terrell Russell]
- [#3] allow genquery2_test to work under all Python2/3 versions [Daniel Moore]
- [#3] call assertRaisesRegex[p] with/without final 'p' (depends on Python 2 or 3) [Daniel Moore]
- [#534] implement replica truncate [Daniel Moore]
- [#584] load settings from environment even without use of config file [Daniel Moore]
- [#600] Comment out test_files_query_case_sensitive BETWEEN tests [Alan King]
- [#597] genquery2_test: Replace Postgres-specific assertions [Alan King]
- [#566] Rename login_auth_test.py to prevent running with full suite [Alan King]
- [#533][#556] implement library features [Daniel Moore]
- [#537] add --help option to the script setupssl.py [Daniel Moore]
- [#574] rename progress_bar to updatables, allow for genericity [Daniel Moore]
- [#574] Allow for tqdm progress bars to be used [Raoul Schram]
- [#586] implement xml_mode() in a new irods.helpers module [Daniel Moore]
- [#558] iRODSAccess: Handle non-str types in constructor [Alan King]
- [#558] Add tests for iRODSAccess constructor type checking [Alan King]
- [#567] return logging to normal after a run of the pool_test [Daniel Moore]
- [#3][#562] skip issue 562 (leaking connections) test for Python2 [Daniel Moore]
- [#565] Descend Bad_AVU_Value from ValueError [Daniel Moore]
- [#587] unique_name now hashes the call tuple for a random seed. [Daniel Moore]
- [#3][#525] allow touch API tests to run on Python 2 [Daniel Moore]
- [#532,#564,#569] fix stored connections to match desired connection timeout. [Daniel Moore]
- [#562] release old connection when redirecting [Daniel Moore]
- [#576] test admin mode in metadata.apply_atomic_operations [Daniel Moore]
- [#576] Add missing admin_mode in JSON message for metadata.apply_atomic_operations [Paul Borgermans]
- [#571] exclude collection "/" from subcollections [Daniel Moore]
- [#557] de-duplicate acl lists in case of multiple replicas. [Daniel Moore]
- [#525] Add support for touch API operation. [Kory Draughn]
- [#535] Implement basic support for GenQuery2 [Sietse Snel]
- [#547] unify AVU field exceptions interface for metadata add and set [Daniel Moore]
- [#550] Add support for client hints [Sietse Snel]

## [v2.0.1] - 2024-04-30

- [#543] Fix issue with parallel downloads to a directory [Raoul Schram]
- [#521] clearer documentation and errors regarding pam/pam_password [Daniel Moore]
- [#518] preserve login_<auth-type> internally generated exceptions [Daniel Moore]
- [#522][#523] allow '=' and ';' in PAM passwords [Daniel Moore]
- [#519] force verify mode to CERT_NONE if irods verify setting is explicitly none [Daniel Moore]
- [#526] can now opt out of strong primes to speed up SSL & PAM tests [Daniel Moore]
- [#3] make sure tempfile.mktemp imported where needed for tests [Daniel Moore]
- [#3] tweak compatibility to iRODS 4.3.2 [Daniel Moore]
- [#539] iRODS 4.3.2 rmgroup adaptation [Daniel Moore]

## [v2.0.0] - 2024-02-12

- [#3] version bump for 2.0.0 [Terrell Russell]
- [#3] update project description [Terrell Russell]
- [#495] append modes seek to end on data_object.open(...) [Daniel Moore]
- [#510] update README to reflect removal of session.permissions [Terrell Russell]
- [#510] change permissions to acls [Daniel Moore]
- [#504] modify replicate/trim code snippet and description [Daniel Moore]
- [#459] respect the default_resource setting for replication [Daniel Moore]
- [#484,#509] Update version mentioned in README for Quota [Terrell Russell]
- [#503] swap readme from .rst to markdown [Terrell Russell]
- [#484] change to proper RST marker "::" in quotas section [Daniel Moore]
- [#485][#430][#494] document new legacy_auth.pam.* settings [Daniel Moore]
- [#501] context manager to temporarily alter settings [Daniel Moore]
- [#430][#494][#498] client auth "plugins" / pam_password compatibility / TTL fix [Daniel Moore]
- [#485] allow detection of config without actually loading it. [Daniel Moore]
- [#462][#399] Default the dataSize to 0 and prefer DATA_SIZE_KW over seek [Daniel Moore]
- [#497] suppress fatal errors when loading configuration [Daniel Moore]
- [#485][#489] document available settings and override environment variables [Daniel Moore]
- [#489] allow environment variable overrides of individual settings during autoload [Daniel Moore]
- [#485] writeable_properties including xml parser [Daniel Moore]
- [#484] Add quotas to README [Daniel Moore]
- [#474][#479] Allow querying, setting, and removing quotas [Daniel Moore]
- [#483] make PRC version available as tuple [Daniel Moore]

## [v1.1.9] - 2023-10-13

- [#471][#472] allow save, load, and autoload of configuration [Daniel Moore]
- [#456] auto-close data objects that go out of scope [Daniel Moore]
- [#455] remove ticket check [Daniel Moore]
- [#452] implement client redirection to resource server [Daniel Moore]
- [#455] introduce low level ticket api changes [Daniel Moore]
- [#234] Implement case-insensitive queries [Sietse Snel]

## [v1.1.8] - 2023-05-18

- [#450] test for setting/getting comments [Daniel Moore]
- [#377] fix iRODSSession connection timeout [Daniel Moore]
- [#450] Get property comments from replica object [Gwenael Leysour de Rohello]
- [#448] protect against bad parameters in modify_password [Daniel Moore]
- [#442] allow non-default string types in AVU fields [Daniel Moore]
- [#443] add NotLike (GenQuery 'NOT LIKE') operator [Daniel Moore]

## [v1.1.7] - 2023-03-28

- [#435] unregister can target a single replica [Daniel Moore]
- [#434] metadata calls now require AVU fields to be nonzero-length strings [Daniel Moore]
- [#431][irods/irods#6921] filter user_id results from R_OBJT_ACCESS through IDs still in R_USER_MAIN [Daniel Moore]
- [#3] acls.set needs admin=True for some tests [Daniel Moore]
- [#3] compatibility bump to iRODS 4.3.1 [Daniel Moore]
- [#426][#428][#429] groupadmin capabilities update [Daniel Moore]

## [v1.1.6] - 2023-01-18

- [#420][#422] present appropriate iRODSAccess.codes, in sorted order [Daniel Moore]
- [#420] store integer codes & strings for access levels [Daniel Moore]
- [#418] raise error in test for IRODS_VERSION mismatch [Daniel Moore]
- [#379] define RE_RUNTIME_ERROR exception [Daniel Moore]
- [#400] more advanced iRODSException representation [Daniel Moore]
- [#392] add iRODSResource properties: parent_name, parent_id, hierarchy_string [Daniel Moore]
- [#243] enable RESC_HIER_STR_KW and RESC_NAME_KW in data open() [Daniel Moore]
- [#395][#396] test of acls manager [Daniel Moore]
- [#396] Introduce "acls" manager and deprecate "permissions" [Daniel Moore]
- [#395] include user_type in permissions [Daniel Moore]
- [#410] ensure a call to iRODSSession.cleanup() at interpreter exit [Daniel Moore]
- [#406] correctly generate ssl context [Daniel Moore]
- [#404] Fix password_obfuscation in Windows [J.P. Mc Farland]
- [#374] Use alternate endpoint for groupadmin requests [Martin Jaime Flores Jr]
- [#5] minor README fix: XML_Parser_Type code sample [Sietse Snel]
- [#5] adds module loading to RErrorStack example [John Constable]

## [v1.1.5] - 2022-09-21

- [#383] correct logical path normalization [Daniel Moore]
- [#369] remove dynamic generation of message classes [Daniel Moore]
- [#386][#389] only load timestamps when requested [Daniel Moore]
- [#386] initial change to add create and modify times for metadata [Paul Borgermans]

## [v1.1.4] - 2022-06-29

- [#372] eliminate SyntaxWarning ("is" operator being used with a literal) [Daniel Moore]
- [#358] eliminate fcntl import [Daniel Moore]
- [#368] ensure connection is finalized properly [Daniel Moore]
- [#362] escape special characters in PAM passwords [Daniel Moore]
- [#364] allow ADMIN_KW in all metadata operations [Daniel Moore]
- [#365] allow set() method via iRODSMetaCollection [Daniel Moore]
- [#3] update tests for 4.3.0 [Daniel Moore]
- [irods/irods#844] fix access_test [Daniel Moore]
- [#3][irods/irods#6124] adapt for ADMIN_KW in post-4.2.11 ModAVUMetadata api [Daniel Moore]
- [#3][irods/irods#5927] test_repave_replica now passes in iRODS >= 4.2.12 [Daniel Moore]
- [#3][irods/irods#6340] test_replica_number passes on 4.3.0 [Daniel Moore]

## [v1.1.3] - 2022-04-07

- [#356] Removing call to partially unsupported getpeername() [Kaivan Kamali]

## [v1.1.2] - 2022-03-15

- [#3][#345] Allow tests to pass and accommodate older Python [Daniel Moore]
- [#352] Fix the infinite loop issue when sock.recv() returns an empty buffer [Kaivan Kamali]
- [#345] Fix connection destructor issue [Kaivan Kamali]
- [#351] replace 704 api constant with AUTH_RESPONSE_AN [Daniel Moore]
- [#350] password input to AUTH_RESPONSE_AN should be string [Daniel Moore]
- [#315] skip cleanup() if session.pool is None [Daniel Moore]
- [#290] only anonymous user can log in without password [Daniel Moore]
- [#43][#328] reasonable indentation [Daniel Moore]
- [#328] allow user to change own password [Daniel Moore]
- [#343][#21] document testing and S3 setup [Daniel Moore]
- [#343] allow parallel (multi-1247) data transfer to/from S3 [Daniel Moore]
- [#332] capitalize -C,-R object type abbreviations [Daniel Moore]
- [#349] normalize() argument not necessarily absolute [Daniel Moore]
- [#323] remove trailing slashes in collection names [Daniel Moore]

## [v1.1.1] - 2022-01-31

- [#338] clarify Python RE Plugin limitations [Daniel Moore]
- [#339] correction to README regarding RULE_ENGINE_ERROR [Daniel Moore]
- [#336] rule files can now be submitted from a memory file object [Daniel Moore]

## [v1.1.0] - 2022-01-20

- [#334] add SECURE_XML to parser selection [Daniel Moore]
- [#279] allow long tokens via PamAuthRequest [Daniel Moore]
- [#190] session_cleanup is optional after rule execution. [Daniel Moore]
- [#288] Rule execute method can target an instance by name [Daniel Moore]
- [#314] allow null parameter on INPUT line of a rule file [Daniel Moore]
- [#318] correction for unicode name queries in Python 2 [Daniel Moore]
- [#170] fixes for Python2 / ElementTree compatibility [Daniel Moore]
- [#170] Fix exception handling QuasiXML parser [Sietse Snel]
- [#170] Parse current iRODS XML protocol [Chris Smeele]
- [#306] test setting/resetting inheritance [Daniel Moore]
- [#297] deal with CHECK_VERIFICATION_RESULTS for checksums [Daniel Moore]
- [irods/irods#5933] PRC ticket API now working with ADMIN_KW [Daniel Moore]
- [#292] Correct tickets section in README [Daniel Moore]
- [#290] allow skipping of password file in anonymous user case [Daniel Moore]
- [irods/irods#5954] interpret timestamps as UTC instead of local time [Daniel Moore]
- [#294] allow data object get() to work with tickets enabled [Daniel Moore]
- [#303] Expose additional iRODS collection information in the Collection object. [Ruben Garcia]
- [#143] Use unittest-xml-reporting package, move to extra [Michael R. Crusoe]
- [#299] Added GenQuery support for tickets. [Kory Draughn]
- [#285] adds tests for irods/irods#5548 and irods/irods#5848 [Daniel Moore]
- [#281] honor the irods_ssl_verify_server setting. [Daniel Moore]
- [#287] allow passing RError stack through CHKSUM library call [Daniel Moore]
- [#282] add NO_COMPUTE keyword [Daniel Moore]

## [v1.0.0] - 2021-06-03

- [#274] calculate common vault dir for unicode query tests [Daniel Moore]
- [#269] better session cleanup [Daniel Moore]

## [v0.9.0] - 2021-05-14

- [#269] cleanup() is now automatic with session destruct [Daniel Moore]
- [#235] multithreaded parallel transfer for PUT and GET [Daniel Moore]
- [#232] do not arbitrarily pick first replica for DEST RESC [Daniel Moore]
- [#233] add null handler for irods package root [Daniel Moore]
- [#246] implementation of checksum for data object manager [Daniel Moore]
- [#270] speed up tests [Daniel Moore]
- [#260] [irods/irods#5520] XML protocol will use BinBytesBuf in 4.2.9 [Daniel Moore]
- [#221] prepare test suite for CI [Daniel Moore]
- [#267] add RuleExec model for genquery [Daniel Moore]
- [#263] update documentation for connection_timeout [Terrell Russell]
- [#261] add temporary password support [Paul van Schayck]
- [#257] better SSL examples [Terrell Russell]
- [#255] make results of atomic metadata operations visible [Daniel Moore]
- [#250] add exception for SYS_INVALID_INPUT_PARAM [Daniel Moore]

## [v0.8.6] - 2021-01-22

- [#244] added capability to add/remove atomic metadata [Daniel Moore]
- [#226] Document creation of users [Ruben Garcia]
- [#230] Add force option to data_object_manager create [Ruben Garcia]
- [#239] to keep the tests passing [Daniel Moore]
- [#239] add iRODSUser.info attribute [Pierre Gay]
- [#239] add iRODSUser.comment attribute [Pierre Gay]
- [#241] [irods/irods_capability_automated_ingest#136] fix redundant disconnect [Daniel Moore]
- [#227] [#228] enable ICAT entries for zones and foreign-zone users [Daniel Moore]

## [v0.8.5] - 2020-11-10

- [#220] Use connection create time to determine stale connections [Kaivan Kamali]

## [v0.8.4] - 2020-10-19

- [#221] fix tests which were failing in Py3.4 and 3.7 [Daniel Moore]
- [#220] Replace stale connections pulled from idle pools [Kaivan Kamali]
- [#3] tests failing on Python3 unicode defaults [Daniel Moore]
- [#214] store/load rules as utf-8 in files [Daniel Moore]
- [#211] set and report application name to server [Daniel Moore]
- [#156] skip ssh/pam login tests if user doesn't exist [Daniel Moore]
- [#209] pam/ssl/env auth tests imported from test harness [Daniel Moore]
- [#209] store hashed PAM pw [Daniel Moore]
- [#205] Disallow PAM plaintext passwords as strong default [Daniel Moore]
- [#156] fix the PAM authentication with env json file. [Patrice Linel]
- [#207] add raw-acl permissions getter [Daniel Moore]

## [v0.8.3] - 2020-06-05

- [#3] remove order sensitivity in test_user_dn [Daniel Moore]
- [#5] clarify unlink specific replica example [Terrell Russell]
- [irods/irods#4796] add data object copy tests [Daniel Moore]
- [#5] Additional sections and examples in README [Daniel Moore]
- [#187] Allow query on metadata create and modify times [Daniel Moore]
- [#135] fix queries for multiple AVUs of same name [Daniel Moore]
- [#135] Allow multiple criteria based on column name [Daniel Moore]
- [#180] add the "in" genquery operator [Daniel Moore]
- [#183] fix key error when tables from order_by() not in query() [Daniel Moore]
- [#5] fix ssl example in README.rst [Terrell Russell]

## [v0.8.2] - 2019-11-13

- [#8] Add PAM Authentication handling (still needs tests) [Mattia D'Antonio]
- [#5] Remove commented-out import [Alan King]
- [#5] Add .idea directory to .gitignore [Jonathan Landrum]
- [#150] Fix specific query argument labeling [Chris Klimowski]
- [#148] DataObjectManager.put() can return the new data_object [Jonathan Landrum]
- [#124] Convert strings going to irods to Unicode [Alan King]
- [#161] Allow dynamic I/O for rule from file [Mathijs Koymans]
- [#162] Include resc_hier in replica information [Brett Hartley]
- [#165] Fix CAT_STATEMENT_TABLE_FULL by auto closing queries [Chris Smeele]
- [#166] Test freeing statements in unfinished query [Daniel Moore]
- [#167] Add metadata for user and usergroup objects [Erwin van Wieringen]
- [#175] Add metadata property for instances of iRODSResource [Daniel Moore]
- [#163] add keywords to query objects [Daniel Moore]

## [v0.8.1] - 2018-09-27

- [#140] Remove randomization from password test [Alan King]
- [#139] Use uppercase queries in tests [Alan King]
- [#137] Handle filenames with ampersands [Alan King]
- [#126] Add size attribute to iRODSReplica [Alan King]

## [v0.8.0] - 2018-05-03

- Add rescName and replNum awareness. [Hao Xu]
- Document put() method in README.rst. [Terrell Russell]
- Add support for specifying resource hierarchy. [Hao Xu]
- Add modDataObjMeta. [Hao Xu]
- Use socket.recv_into() to speed up file download. [Pierre Gay]
- Lazy load resource children. [Antoine de Torcy]
- Test cleanup. [Antoine de Torcy]
- Add recursive collection creation support, plus test. [Robert Davey]
- Make query instances iterable. [Antoine de Torcy]
- Update package information. [Antoine de Torcy]
- Add version attribute to icat columns. [Antoine de Torcy]
- Don't enforce DB schema in data object constructor. [Antoine de Torcy]
- Add D_RESC_ID to data object model. [Bob Belnap]
- SSL context from iRODSAccount instance attributes. [Antoine de Torcy]
- Avoid calling data object create on replication node. [Antoine de Torcy]
- Pass optional CA file to SSL context. [Antoine de Torcy]
- Graceful SSL shutdown. [Antoine de Torcy]
- Set open flags and IO buffer size in DataObjectManager. [Antoine de Torcy]
- Force open flags to client os independent values. [Pierre Gay]
- Handle Winerror 10045. [Pierre Gay]
- Python 2/3 compability. [Jonathan de Bruin]


## [v0.7.0] - 2017-12-15

- Dynamic instance method definition for Python2/3. [Antoine de Torcy]
- Filter by collection path. [Antoine de Torcy]
- Add truncate flag. [Antoine de Torcy]
- Add update replica keyword. [Antoine de Torcy]
- Client-side support for ALL_KW on put. [Antoine de Torcy]
- Add server version to session properties. [Antoine de Torcy]
- Pass object IO options in unpacked format. [Antoine de Torcy]
- Refactor tests and session config. [Antoine de Torcy]
- First pass at SSL support. [Antoine de Torcy]
- Use reentrant lock in connection pool. [Antoine de Torcy]
- Allow for cases with CS_NEG_DONT_CARE. [Antoine de Torcy]
- First pass at client-server negotiation. [Antoine de Torcy]
- Simplify session/account initialization. [Antoine de Torcy]
- Expect multiple DNs per user. [Antoine de Torcy]
- Use default resource host/path strings. [Antoine de Torcy]
- Honor default resource setting. [Antoine de Torcy]
- Add placeholder for formatting arguments. [Antoine de Torcy]
- Add function get_html_string in results.py. [KERVELLEC Joseph]
- Fix assertions. [Antoine de Torcy]
- Test registration with checksum. [Antoine de Torcy]
- Add admin option to AccessManager.set() [Antoine de Torcy]
- Add file/dir registration. [Antoine de Torcy]
- Remove call to sys.exc_clear() [Antoine de Torcy]
- Force flag support on get. [Antoine de Torcy]
- Fix intermittent encoding error. [Antoine de Torcy]
- Update iRODSSession.configure() [Antoine de Torcy]
- Set default iRODS authentication scheme to native. [Lazlo Westerhof]
- Use the same naming as iRODS environment variable
  irods_authentication_scheme. [Lazlo Westerhof]
- Add connection timeout. [Antoine de Torcy]
- Extend the query condition interface. [Antoine de Torcy]
- Better handling of byte buffers. [Antoine de Torcy]
- Python 3 fix. [Antoine de Torcy]
- Set OPR_TYPE to 1 on put. [Antoine de Torcy]
- Set default empty username in iRODSAccess. [Antoine de Torcy]
- Add ability to set user passwords. [Antoine de Torcy]
- First pass at iRODS ticket support - ticket generation - ticket based
  access. [Antoine de Torcy]
- Add dependencies to setup.py. [Antoine de Torcy]
- Add object put/get test. [Antoine de Torcy]
- Unpack error messages. [Antoine de Torcy]
- Add CAT_UNKNOWN_SPECIFIC_QUERY exception. [Antoine de Torcy]
- Commits for the english language, which apparently I'm qualified in..
  [John Constable]
- Document the use of the SpecificQuery class and irods_environment.json
  reading functionality. [John Constable]
- Adds exists() to data_object manager to mirror collection manager.
  [Alex Lemann]
- Remove unused exceptions. [Antoine de Torcy]
- Fix exception hierarchy. [Antoine de Torcy]


## [v0.6.0] - 2017-05-23

- Patch for GSI. [pdonorio]
- Add keywords for atomic put. [Antoine de Torcy]
- Raise recv error. Don't call exit() [Alex Lemann]
- Allows numThreads to be configured in session. [Alex Lemann]
- Python 3 fix. [Antoine de Torcy]
- Encode unicode when packing. [Antoine de Torcy]
- Optional use of icommands environment files. [Antoine de Torcy]
- Support for user certificate management. [Antoine de Torcy]
- Add oprType to data object open options. [Antoine de Torcy]
- Unit tests. [Antoine de Torcy]
- Set OprType for data object copy. [Antoine de Torcy]
- Adding support for data object copy. [cmart]
- Add replica number to iRODSReplica. [Antoine de Torcy]
- Add unit test to list queries. [Antoine de Torcy]
- SQL query support. [Antoine de Torcy]
- Add replica example to README. [Antoine de Torcy]
- Update test. [Antoine de Torcy]
- Update README.md. [Antoine de Torcy]
- Move iRODSDataObject.open() code to manager. [Antoine de Torcy]
- Support for optional keywords on open. [Antoine de Torcy]
- Python 3.4+ support. [Paolo D]
- Update test. [Antoine de Torcy]
- Change wrong irods exception. [Simon Artzet]
- Added password obfuscation/de-obfuscation utilities from iRODS main.
  [Zoey Greer]
- Cleanup. [Antoine de Torcy]
- Lazy import gssapi. [Antoine de Torcy]
- Cleanup. [Antoine de Torcy]
- Refactor tests. [Antoine de Torcy]
- Fixing problems for unittests. [pdonorio]
- Add tests for GSI authentication. [pdonorio]
- Add GSI authentication to Python client. [pdonorio]
- Remove logging and update version. [Antoine de Torcy]
- Fix ExecCmdOut_PI unpacking. [Antoine de Torcy]
- Update README.md. [Antoine de Torcy]
- Support for MsParam_PI packing/unpacking. [Antoine de Torcy]
- Update README.md. [Antoine de Torcy]
- Use comma as delimiter. [Antoine de Torcy]
- First pass at rule execution support. [Antoine de Torcy]
- Support for resource context management. [Antoine de Torcy]
- Fix resource model. [Antoine de Torcy]
- First pass at support for resource hierarchies. [Antoine de Torcy]
- Handle missing socket.MSG_WAITALL flag. [Antoine de Torcy]
- Example of query with 'like' condition. [Antoine de Torcy]
- Check for empty values before sending add metadata request. [Antoine
  de Torcy]
- PEP8 compliance. [Antoine de Torcy]
- Unit test. [Antoine de Torcy]
- First pass at data object replication. [Antoine de Torcy]

## [v0.5.0] - 2016-08-15

- Update package files. [Antoine de Torcy]
- Add set operation for metadata. [Illyoung Choi]
- Add truncate function to data_object class and test case for it.
  [Illyoung Choi]
- Support truncate operation. [Illyoung Choi]
- Test for PEP based checksum computation. [Antoine de Torcy]
- Add jenkins test status. [Antoine de Torcy]
- Add tests for connection pooling. [Matthew R Hanlon]
- NetworkException on disconnect should still release the connection.
  [Matthew R Hanlon]
- Remove idle connections from pool on release. [Matthew R Hanlon]
- Catch formatting exceptions. [Antoine de Torcy]
- Do not rely on socket.MSG_WAITALL flag since it doesn't guarantee a
  message will be in exact requested len when interrupt occurs.
  [Illyoung Choi]
- Consecutive open/read tests. [Antoine de Torcy]
- Use generator to get subcollections and objects in collection manager.
  [Antoine de Torcy]
- Typo. [Antoine de Torcy]
- Fix aggregation example in README. [Wataru Takase]
- Add aggregation feature for query. [Wataru Takase]
- Update setup and README. [Antoine de Torcy]
- Collection ACL + test. [Antoine de Torcy]
- Cleanup. [Antoine de Torcy]
- First pass at ACL management. [Antoine de Torcy]
- Fix naming. [Antoine de Torcy]
- Update test group size. [Antoine de Torcy]
- First pass at user group management. [Antoine de Torcy]
- Dropping unofficial support for Python 2.6. [Antoine de Torcy]
- Remove leftover resource group reference. [Antoine de Torcy]
- Add force flag to DataObjectManager.unlink() + test. [Antoine de
  Torcy]
- Typo. [Terrell Russell]
- Update README. [Antoine de Torcy]
- Make resource management backward compatible. [Antoine de Torcy]
- Strip gen queries going to older servers. [Antoine de Torcy]
- Update README. [Antoine de Torcy]
- Support for moving objects and collections. [Antoine de Torcy]
- Better support for unicode strings. [adetorcy]
- Updated README.md. [Antoine de Torcy]
- Test cleanup. [Antoine de Torcy]
- Added responses to collOprStat calls from the server in the collection
  manager. [Antoine de Torcy]
- Added generator method to Query. [Antoine de Torcy]
- Updated DataObject model and tests. [Antoine de Torcy]
- Patch by @lewisct. [Antoine de Torcy]
- More resource mangement + tests. [Antoine de Torcy]
- Added optional parameters to DataObjectManager.create() [Antoine de
  Torcy]
- Added resource management support. [Antoine de Torcy]
- Updated resource model (with context, parent, children, etc...)
  [Antoine de Torcy]
- First stab at user modification and resource management support.
  [Antoine de Torcy]
- New lines. [Antoine de Torcy]
- Support for user creation and deletion + tests. [Antoine de Torcy]
- Fixed Query._clone() [Antoine de Torcy]
- Sort results in metadata test to avoid mixup in assertion. [Antoine de
  Torcy]
- Removed resource groups and resc_info for 4.1. [Antoine de Torcy]
- Typo. [Antoine de Torcy]
- Update version. [J. Matt Peterson]
- Test results update. [Antoine de Torcy]
- Test results update. [Antoine de Torcy]
- Use test credentials from config module. [Antoine de Torcy]
- Comments. [Antoine de Torcy]
- Updated API and packing instructions for FileCloseRequest() [Antoine
  de Torcy]
- Update to new API for collection creation. [Matthew Turk]
- Update setup.py. [Low Kian Seong]
- Change for initial pypi release.        modified:   .gitignore  new
  file:   AUTHORS     new file:   CHANGES     new file:   LICENSE
  new file:   MANIFEST.in         modified:   setup.py. [J. Matt
  Peterson]
- Upped to version 0.3. [Chris LaRose]
- Destroying connections that encounter broken pipes. This makes
  connections more resiliant to connection resets by the iRODS host.
  [Chris LaRose]
- Upped version number. [Chris La Rose]
- Added iRODSReplica class. [Chris La Rose]
- Getting data_objects of a collection where there exists replicas no
  longer returns duplicate data_objects. [Chris La Rose]
- DataObjectManager.get now no longer fails when trying to get a data
  object that is replicated. DataObject now stores a list of four-tuples
  representing its replicas. [Chris La Rose]
- Added repr method for column. [Chris La Rose]
- Corrected typo in exception. [Chris La Rose]
- Thread safe connection pool. [Falmarri]
- Replaced instances of logging.{debug, info, warn, error} with
  logging.getLogger(__name__).{debug, info, warn, error} for better
  logging support. [Christopher La Rose]
- Fixed closing files. [Chris La Rose]
- Reimplemented buffered reading and writing with new io module. [Chris
  La Rose]
- Fix bug where port keyword didn't work if it was a string. [J. Matt
  Peterson]
- Fixed null comparison. [Christopher La Rose]
- Readlines is a generator. [Falmarri]
- Implmented iRODSDataObjectFile.[readline(), readlines()] [Chris
  LaRose]
- Changed project name in setup. [Chris LaRose]
- Rename from pycommands to python-irodsclient. [JMatt Peterson]
- Consolidate tests. [Michael Gatto]
- Update TODOs. [Chris LaRose]
- Updated install link in readme. Updated TODOs. [Chris LaRose]
- Major test restructuring. [Michael Gatto]
- Minor change. [Michael Gatto]
- Run all tests at once, if desired. [Michael Gatto]
- Added license. [Chris La Rose]
- Added convenience methods for removing data objects and collections.
  Renamed CollectionManager.[delete=>remove] [Chris La Rose]
- Removed useless file. [Chris La Rose]
- Updated version to 0.1. [Steve Gregory]
- Update README.md with proxy instructions. [Chris LaRose]
- Remove double import. [Michael Gatto]
- Update results. [Michael Gatto]
- Add heading for test results. [Michael Gatto]
- Rename to match naming convention of rest of tests in this package.
  [Michael Gatto]
- Moved tests to own package within the irods package. [Michael Gatto]
- Placed client_user and client_zone properties onto the iRODSAccount
  class. [Chris La Rose]
- Ignore commonly-produced cruft files. [Michael Gatto]
- Added walk() implementation to collection. [Steve Gregory]
- StatupPack construction works for proxying a user. [Chris La Rose]
- Added ability to initialize session with proxy_user and proxy_zone
  options. [Chris La Rose]
- Absolute imports in all the modules! [Chris La Rose]
- Resource manager files all now use absolute imports. [Christopher La
  Rose]
- Moved resource managers into self contained module. [Chris LaRose]
- Fixed prettytable requirement in setup.py. [Chris LaRose]
- Formatting readme. [Chris La Rose]
- Added note about python 2.7 requirement. [Chris La Rose]
- Added missing import statement. [Chris La Rose]
- Queries now support order_by. [Chris La Rose]
- Removed logging. [Chris La Rose]
- Implemented ordering on queries. [Chris La Rose]
- Added print statement for results in readme. [Chris La Rose]
- Implemented query._clone() [Chris La Rose]
- Added query offsets. [Chris La Rose]
- Added ability to remove collections. [Chris La Rose]
- Added ability to create new collections. [Chris La Rose]
- Added pretttable output to readme. [Chris La Rose]
- Result objects will now print a prettytable. [Chris La Rose]
- Fixed setup script. [Chris La Rose]
- Added prettytable as a dependency. [Chris La Rose]
- Implemented Query.first() and Query.one() [Chris La Rose]
- Adding and removing metadata can now be performed with positional
  arguments instead of iRODSMeta objects. [Chris La Rose]
- Manager method renaming. [Chris La Rose]
- Cleaning up managers. [Chris La Rose]
- Fixed references in managers to session. [Chris La Rose]
- Added appropriate imports. [Chris La Rose]
- Made a bunch of manager classes.  Nothing likely works. [Chris La
  Rose]
- Removed logging statements. [Chris La Rose]
- Added note about gen queries in readme. [Chris La Rose]
- Fixed file create, metadata add. [Chris La Rose]
- Added note about file iteration in readme. [Chris La Rose]
- Files are now iterable. [Chris La Rose]
- Fixed file seek. [Chris La Rose]
- Spelling mistakes. [Chris La Rose]
- Added collection message. [Chris La Rose]
- Added browse test. [Chris La Rose]
- Began to rename messages. [Chris La Rose]
- Basic connection pool now reusing connections. [Chris La Rose]
- Added option to data_object_file to close file descriptor after full
  read. [Chris La Rose]
- Release connections even after a failure to close a file. [Chris La
  Rose]
- Fixed type error when trying to read a file with no specified size.
  [Chris La Rose]
- Added checksum and timestamp attributes to data objects. [Chris La
  Rose]
- Failed collection request for a data object rasies
  DataObjectDoesNotExist. [Chris La Rose]
- Forced file operations to be performed on the same connection. [Chris
  La Rose]
- Added account, connection, and pool classes. [Chris La Rose]
- Added iRODSMeta.__dict__ [Chris La Rose]
- Unbroke collection metadata. [Chris La Rose]
- Unbroke dataobject.read() [Chris La Rose]
- Renamed read_all to read_gen. [Chris La Rose]
- Corrected subcollection query. [Chris La Rose]
- Corrected dataobject.read_all() [Chris La Rose]
- Changed visibility of iRODSDataObject.read_all() to public. [Chris La
  Rose]
- Added DoesNotExist exceptions. [Chris La Rose]
- Corrected data object path. [Chris La Rose]
- Collection and data object both now have normalized name and path
  attributes. [Chris La Rose]
- Added installation instructions. [Chris La Rose]
- Fixed ability to initialize session without account parameters. [Chris
  La Rose]
- Added message module to setup.py. [Chris La Rose]
- Added session.configure. [Chris La Rose]
- Replaced py_modules with packages in setup. [Chris La Rose]
- More setup. [Chris La Rose]
- More setup. [Chris La Rose]
- Correct invalid module in setup.py. [Chris La Rose]
- Added setup.py. [Chris La Rose]
- Update readme. [Chris La Rose]
- Updated readme. [Chris La Rose]
- Updated readme, fixed error when deleting meta with null units. [Chris
  La Rose]
- Fixed metadata for collections. [Chris La Rose]
- Update readme. [Chris La Rose]
- Closing file descriptors after creating new data objects. [Chris La
  Rose]
- Updated todos. [Chris La Rose]
- Corrected syntax mistakes in iRODSMetaCollection. [Chris La Rose]
- Null result sets return empty lists instead of raising exceptions.
  [Chris La Rose]
- Fixed runtime errors. [Chris La Rose]
- Added todo. [Chris La Rose]
- Added todos. [Chris La Rose]
- Added meta.iRODSMetaCollection. [Chris La Rose]
- Modified session metadata api to accept model classes. [Chris La Rose]
- Update README.md. [Chris LaRose]
- Added iRODSSession.{add_meta, remove_meta, copy_meta} [Chris La Rose]
- IRODSSession.get_meta now returns a list of type iRODSMeta. [Chris La
  Rose]
- Added ability to query metadata. [Chris La Rose]
- Updated todos. [Chris La Rose]
- Supporting ability to delete data objects. [Chris La Rose]
- Update README.md. [Chris LaRose]
- Formatted task list. [Chris La Rose]
- Added todo list to readme. [Chris La Rose]
- Updated readme with file creation. [Chris La Rose]
- Added iRODSSession.create_data_object. [Chris La Rose]
- Added default port to irods session. [Chris La Rose]
- Added ability to use with statement for irods file objects. [Chris La
  Rose]
- Added wait all flag on receiving sockets. [Chris La Rose]
- Changed read all size. [Chris La Rose]
- Added ability to read entire file. [Chris La Rose]
- Added ability to close files. [Chris La Rose]
- File seek support. [Chris La Rose]
- Now supporting writing to existing files. [Chris La Rose]
- Added cases for open flags. [Chris La Rose]
- Added default file read size. [Chris La Rose]
- Successfully reading file contents. [Chris La Rose]
- Sending data read message. [Chris La Rose]
- Removed unnecessary constants. [Chris La Rose]
- Changed api_numbers to dict. [Chris La Rose]
- Added magic numbers for api calls. [Chris La Rose]
- Added data object file class. [Chris La Rose]
- Received messages raise the appropriate error response. [Chris La
  Rose]
- Added all exceptions as classes. [Chris La Rose]
- Successfully opening file for reading. [Chris La Rose]
- Short readme addition for data objects. [Chris La Rose]
- Removed old messages file. [Chris La Rose]
- Result set str formatting. [Chris La Rose]
- Correctly forming result sets. [Chris La Rose]
- Correct representation of empty map messages. [Chris La Rose]
- Tests passing again. [Chris La Rose]
- Corrected construction of gen query inp messages. [Chris La Rose]
- Fixed login. [Chris La Rose]
- Added data obj inp. [Chris La Rose]
- Cleanup. [Chris La Rose]
- Changed unpacking convention to allow for arrays of submessages.
  [Chris La Rose]
- Added sql result test. [Chris La Rose]
- Finished gen query inp test. [Chris La Rose]
- Added test for gen query inp. [Chris La Rose]
- Added message init method for convenience. [Chris La Rose]
- Added test for key value pair. [Chris La Rose]
- Added test for inxivalpair. [Chris La Rose]
- Binary property now properly performs base64 encoding and decoding.
  [Chris La Rose]
- Added test for startuppack. [Chris La Rose]
- Added unit test file. [Chris La Rose]
- Renamed test. [Chris La Rose]
- Fixed array and submessage unpacking. [Chris La Rose]
- Added unpacking. [Chris La Rose]
- Fixed submessage property. [Chris La Rose]
- Fixed array property. [Chris La Rose]
- AuthResponseInp_PI proof of concept. [Chris La Rose]
- Added some messages. [Chris La Rose]
- Removed irrelevant _format property of Message classes. [Chris La
  Rose]
- Beginning to reimplement messages. [Chris La Rose]
- Moved old messages into tempory file. [Chris La Rose]
- Property.format is no longer static. [Chris La Rose]
- Redefined property packing for more flexibility. [Chris La Rose]
- Added message.pack method. [Chris La Rose]
- Added ordered properties. [Chris La Rose]
- Added DataObjInp message. [Chris La Rose]
- Removed session.collection_exists. [Chris La Rose]
- Added some exceptions. [Chris La Rose]
- Added syntax highlighting to readme. [Chris LaRose]
- Formatting headers of result set string representation. [Chris La
  Rose]
- Added missing fields to DataObject model. [Chris La Rose]
- Added collection.subcollections and collection.data_objects. [Chris La
  Rose]
- Added session.get_data_object. [Chris La Rose]
- Corrected formatting of datetime columns in queries. [Chris La Rose]
- Convert irods timestamsp to datetime.datetime objs. [Chris La Rose]
- Update README.md. [Chris LaRose]
- Reimplemented result sets, added session.get_collection. [Chris La
  Rose]
- Formatted result sets as a list of dictionaries. [Chris La Rose]
- Fixed 'not equal' operator for criteria. [Chris La Rose]
- Changed nameds of startup pack and auth response messages to match
  irods api. [Chris La Rose]
- Added ResultSet class with a __str__ method that prints a result set
  as a table SQL style. [Chris La Rose]
- Added Zone and Resource models. [Chris La Rose]
- Added iRODSException class. [Chris La Rose]
- Added query.first() placeholder. [Chris La Rose]
- Create README.md. [Chris LaRose]
- GenQueryInp constructor now accepts messages instead of strings.
  [Chris La Rose]
- Added GenQueryOut unapcking. [Chris La Rose]
- Changed column name on data object. [Chris La Rose]
- Added dataobject model. [Chris La Rose]
- Added GenQueOut message. [Chris La Rose]
- Added test for collection existance. [Chris La Rose]
- Added auth check for session.execute_query() [Chris La Rose]
- Special cases for keyval pair and inxival pair messages when length is
  0. [Chris La Rose]
- Added query.all(), session.execute_query() [Chris La Rose]
- Added general query message. [Chris La Rose]
- Added query._kw_message() [Chris La Rose]
- Added query._conds_message() [Chris La Rose]
- Added InxValPair. [Chris La Rose]
- Added query._select_message() [Chris La Rose]
- Added InxIvalPair message. [Chris La Rose]
- Completed keyword implementation. [Chris La Rose]
- Added QueryKey which is a superclass of Column and Keyword. [Chris La
  Rose]
- Added Query.filter. [Chris La Rose]
- Query object now maintains a dict of columns. [Chris La Rose]
- Added Query class. [Chris La Rose]
- Model metaclass now stores only a list of columns, not their
  associated attribute names. [Chris La Rose]
- Added model base class. [Chris La Rose]
- Added Criterion class. [Chris La Rose]
- Added columns.py. [Chris La Rose]
- Added magic numbers. [Chris La Rose]
- Added models. [Chris La Rose]
- Added comments for packing instructions for gen query. [Chris La Rose]
- IRODSMessage must be of type MainMessage now. [Chris La Rose]
- Added file.py. [Chris La Rose]
- Removed hardcoded username and password. [Chris La Rose]
- Added session destructor. [Chris La Rose]
- Added logging. [Chris La Rose]
- Added MAX_PASSWORD_LENGTH constant. [Chris La Rose]
- Added message.StartupMessage. [Chris La Rose]
- Added message and session classes. [Chris La Rose]
- Successfully disconnnecting. [Chris La Rose]
- Initial commit. [Chris La Rose]
