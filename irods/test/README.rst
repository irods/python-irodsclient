Running all or part of the Python iRODS Client test suite
---------------------------------------------------------

The test suite is based on assertions that use the unittest module. Regarding the test output:  FAIL (or F) or ERROR (or E) is bad; "ok" or "."
means a passing result.

There are several ways to run the suite.  All require the user running them to have prepared an irods environment (located in ~/.irods)
which points at a running server and authenticates as a rodsadmin.

To run specific tests
---------------------

Given the relative imports in the testing files ``from ..message import *``
for example, run the tests as so::

 cd PRC_ROOT_DIR
 python -m unittest irods.test.data_obj_test.TestDataObjOps.test_obj_replicate

You may also run the tests from within the ``irods/test/`` directory::

 python message_test.py


To run the full test suite
--------------------------

::

 python runner.py

This imports all tests in the ``test`` directory and runs them. It will not die upon error.
The script depends on the :code:`xmlrunner` module, so prior to running it, be sure the extra 
"tests" dependency has been installed:

:: 

 pip install python-irodsclient[tests]

The above ensures the installation of the :code:`unittest-xml-reporting` package, which contains
the most current version of the :code:`xmlrunner` module.


Test dependencies
-----------------

A valid account on a running iRODS grid. The tests will use iRODS credentials under ``~/.irods/`` unless the environment variable ``IRODS_ENVIRONMENT_FILE`` is set.
