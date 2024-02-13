# A Topological Setup for Testing the Python Client

The `docker-testing` directory contains the necessary files for building and
running tests from the perspective of a specific client node in a larger network.

We currently allow a choice of Python interpreter and iRODS server to be installed
on the client and provider nodes of a simulated network topology.

The choice of versions are dictated when running the test:

|:------------------:|:---------------:|
|Environment Variable| Valid Range     |
|:-------------------|-----------------|
IRODS_PACKAGE_VERSION|4.3.1 to 5.0.2   |
PYTHON_VERSION       |3.9 to 3.13      |
|:-------------------|-----------------|

Currently the database server is fixed as Postgres.

## Details of usage

The file `$REPO/.github/workflows/run-the-tests.yml`
(where `$REPO` is the `/path/to/local/python-irodsclient` repository)
contains commands for starting the server and client containers and running the PRC
suite in response to a push or pull-request.

The test suite can also be run on any workstation with docker compose installed.
What follows is a short summary of how to run the test configuration at the bench.
It is this procedure which is run within the Github workflows.

   1. cd into top level of $REPO

   2. run:
      ```
      ./docker-testing/start_containers.sh 4.3.4 3.11
      ```
      This builds and runs the docker images for the project,  with "4.3.4" being the iRODS
      version installed on the provider and "3.11" is the version of python run on the client side.

   3. run:
      ```
      docker exec <name-of-python-client-container> /repo_root/docker-testing/run_tests.sh
      ```
      (Note:  `/repo_root` is an actual literal path, internal to the container.)
      You'll see the test output displayed on the console.  At completion, xmlrunner outputs are in /tmp.

   4. use `docker logs -f` with the provider instance name to tail the irods server log output
