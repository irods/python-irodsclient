Tests to be run with docker container and local iRODS server.
-------------------------------------------------------------

These test scripts are meant to be run atop the docker test container
now implemented in a development branch but slated for release in a later version
of python-irodsclient.  (See issue #502.)

Each BATS script is designed such that a "main" function is executed to assert
the relevant test outcomes.  In effect, this is realized because BATS fails the
test if any individual command in the function fails.

The BATS tests are designed to be run by the recipe below:

```
  cd <REPO>/irods/test/scripts
  ../harness/docker_container_driver.sh
```
