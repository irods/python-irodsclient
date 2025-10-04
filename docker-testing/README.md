The file `$REPO/.github/workflows/run-the-tests.yml`
(where `$REPO` is the /path/to/local/python-irodsclient repository)
contains commands for starting the server and client containers and running the PRC
suite in response to a push or pull-request.

The tests suite can also be run on any workstation with "docker compose" installed:

   1. cd into top level of $REPO

   2. run:
      ```
      ./docker-testing/start_containers.sh 3.6
      ```
      This builds and runs the docker images.  "3.6" is the version of python desired.

   3. run:
      ```
      docker exec <name-of-python-client-container> /repo_root/docker-testing/run_tests.sh
      ```
      (Note:  `/repo_root` is an actual literal path, internal to the container.)
      You'll see the test output displayed on the console.  At completion, xmlrunner outputs are in /tmp.

   4. use `docker logs -f` with the provider instance name to tail the irods server log output

DEBUGGING
---------
We can also to run a specific test that we specify by name:

```
$ docker exec -it <name-of-python-client-container> /repo_root/docker_testing/run_tests.sh irods.test.<module>.<class>.<method>
```

Optionally we can also enter the PDB command-line debugger at a place of our choosing in the source code, by stopping on a breakpoint,
and then stepping through code.

The breakpoint can be placed by adding the line

```
import pdb;pdb.set_trace()
```

immediately before the source line in the test code at which we wish to enter the debugger.
