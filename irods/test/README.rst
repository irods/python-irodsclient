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


Test dependencies
-----------------

A valid account on a running iRODS grid. The tests will use iRODS credentials under ``~/.irods/`` unless the environment variable ``IRODS_ENVIRONMENT_FILE`` is set.
