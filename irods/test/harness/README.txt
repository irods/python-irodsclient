SAMPLE RUNS

To build required images
------------------------
Examples

    1) ./build-docker.sh 
       DEFAULT: build  single-node system based on latest iRODS release

    2) IRODS_PACKAGE_VERSION="4.2.12-1~bionic" NO_CACHE='1' ./build-docker.sh 
       Build (ignoring docker cache) single-node system based on specified package version string.

simple examples
---------------
./docker_container_driver.sh  tests/test_1.sh 
./docker_container_driver.sh  tests/test_2.sh 

Any script in a subdirectory of the repo (mounted at /prc within the container) can be
executed and will be able to find other scripts and source include files within the tree.
[See "experiment.sh" example below.]

Examples of options in driver script
------------------------------------

  1. To start container and run test script:
     C=$(  ./docker_container_driver.sh -c -L -u testuser  ../scripts/experiment.sh )

  2. To manually examine results afterward:
     docker exec -it $C bash 


Demo / Demo hook  / args
------------------------

$ ~/python-irodsclient/irods/test/harness$ ./docker_container_driver.sh  ../demo.sh 
ORIGINAL_SCRIPT_RELATIVE_TO_ROOT=[irods/test/demo.sh]
image=[ssl-and-pam]
.......-- HOOK RUNNING --
/prc/irods/test/demo.sh running
args:
1: [arg1]
2: [arg2]
Killed: 1358fbff6eadac24f0915ffb414f0367deedc84b0c3e4de69a23bd3a8726298f
daniel@prec3431:~/python-irodsclient/irods/test/harness$ echo $?
118

