### Test results
[![Build Status](https://jenkins.irods.org/buildStatus/icon?job=test-python-client-4.1.8-ub14)](https://jenkins.irods.org/job/test-python-client-4.1.8-ub14)

### To run a test
Given the relative imports in the testing files `from ..message import *`
for example, run the tests as so:
```
cd PRC_ROOT_DIR
python -m irods.test.message_test
```
You may also run the tests from within the irods/test/ directory:
```
python message_test.py
```

### To run all tests at once
```
python runner.py
```
This imports all tests in the `test` directory and runs them. It will not die upon any errors.

### Test dependencies
A valid account on a running iRODS grid. See `./config.py`.
