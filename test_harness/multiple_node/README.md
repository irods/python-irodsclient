# A Topological Setup for Testing the Python Client

The `docker-testing` directory contains the necessary files for building and
running the client test suite from the perspective of a specific client node
(separate from the iRODS server node it targets for the tests).

The client, provider, and database are currently run on distinct nodes within
a network topology set up by `docker compose` for the tests.

We currently allow a choice of Python interpreter and iRODS server to be installed
on the client and provider nodes, respectively.

The choice of versions are dictated when running the test:

| Environment Variable | Min supported version | Max supported version |
| -------------------- | --------------------- | --------------------- |
| IRODS_PACKAGE_VERSION | 4.3.1 | 5.0.2 |
| PYTHON_VERSION | 3.9 | 3.13 |

Currently the database server is fixed as Postgres.

## Details of usage

The file `.github/workflows/run-the-tests.yml` describes a Github action which
will be started to run the client test suite in response to creating a pull
request, or pushing new commits to the GitHub branch, containing it.

The command-line recipe outlined in the file also supports running the
test suite on any workstation with docker compose installed.

A summary of how to run the tests "at the bench" follows:

   1. Change the working directory to the root directory of the repository, e.g.:
      ```
      cd /path/to/python-irodsclient
      ```

   2. Run:
      ```
      ./docker-testing/start_containers.sh 4.3.4 3.11
      ```
      This builds and runs the docker images for the project, with "4.3.4" being the iRODS
      version installed on the provider and "3.11" being the version of python installed on the client side.

   3. Run:
      ```
      docker exec <client_container_name> /repo_root/docker-testing/run_tests.sh
      ```
      (Note:  `/repo_root` is an actual literal path, internal to the container.)
      You'll see the test output displayed on the console.  At completion, xmlrunner outputs are in 
      `/tmp/python-irodsclient/test-reports`.

   4. Tail docker logs to see the iRODS server log.
      ```
      docker logs -f <provider_container_name>
      ```
