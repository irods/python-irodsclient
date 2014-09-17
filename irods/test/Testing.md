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

Run All Tests at Once
---------------------
```
python runner.py
```

This imports all tests in the `test` directory and runs them. It will not die upon any errors.


Test Dependencies
-----------------

A valid account on a running iRODS grid. See `./config.py`.

Current Test Results
--------------------


| Test        | Status           | Notes |
| ------------- |-------------|------------|
| collection_test.py | OK ||
| connection_test.py | OK ||
| file_test.py | OK ||
| message_test.py | OK ||
| meta_test.py | OK ||
| query_test.py | OK ||

