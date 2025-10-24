# Docker Powered Test Harness

## Description

A series of docker images which support running isolated test scripts (using BATS, bash, or Python).
Once built, the images allow loading and customizing the Docker container environment for a given 
test script.

The general form for test invocation is: `docker_container_driver.sh  <path_to_script_on_host>`

Within the container, a computed internal path to the same script is executed, whether directly or
indirectly by a wrapper script.  The wrapper for many of the PRC authentication-via-PAM tests is
irods/test/login_auth_test.sh.

The test_script_parameters file, located in the irods/test/harness directory, contains customized
settings for each test script run, including:

   - Docker image name to be used.

   - Wrapper to be invoked, if any.  Wrappers shall perform common setup tasks up to and including
     invoking the test script itself.

   - Which user is running the test.  (Unless otherwise specified, this is the passwordless-sudo-
     enabled user `testuser`).

When done with a test, the `docker_container_driver.sh` exit code mirrors the return code from the
run of the test script. The container itself is removed unless the `-L` ("leak") option is given.

## Sample Runs

### To build required images

For our convenience in this doc, set a shell variable `REPOROOT` to `~/python-irodsclient` (or
similar) to specify the path to the top level of the local repository.

Sample command lines to build Docker images:

1. ```
   cd $REPO_ROOT/irods/test/harness
    ./build_docker.sh
   ```

   Builds docker images in proper sequence.

2. ```
   cd $REPO_ROOT/irods/test/harness;
   IRODS_PACKAGE_VERSION=4.3.4 PYTHON_VERSION=3.11 NO_CACHE=1 ./build-docker.sh [ Dockerfiles... ]
   ```

   Builds (ignoring docker cache) images based on specific iRODS package version and desired
   Python Interpreter version, optionally with a restricted list of Docker files in need of rebulding.

### To run a test script.

```
$REPO_ROOT/irods/test/harness/docker_container_driver.sh $REPO_ROOT/irods/test/scripts/run_local_suite
```

For both builder and driver script, the environment variable `DOCKER` may be set to `podman` to run
the alternative container engine.  Otherwise it default to a value of `docker`.
