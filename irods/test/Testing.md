TESTING NOTES
=============

Given the relative imports in the testing files `from ..message import *`
for example, run the tests as so:

```
cd TO_PYCOMMAND_ROOT_DIR
python -m irods.test.message_test
```

You may also run the tests from within the irods/test/ directory:

```
python message_test.py
```

Test Dependencies
-----------------

Testing appears to rely on a local irods directory.

Current Test Results
--------------------


| Test        | Status           | Notes |
| ------------- |-------------|------------|
| browse_test.py | fails  | `File "browse_test.py", line 12, in test_get_collection coll = sess.get_collection(path) AttributeError: 'iRODSSession' object has no attribute 'get_collection'`|
| coll_test.py | fails | requires username, password, host; fixable|
| file_test.py | fails | `File "file_test.py", line 9, in <module> obj = sess.get_data_object("/tempZone/home/rods/test1") AttributeError: 'iRODSSession' object has no attribute 'get_data_object'`|
| message_test.py | ||
| meta_test.py |||
| query_test.py |||
| test_connection.py |||

