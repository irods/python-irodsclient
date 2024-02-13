#!/usr/bin/env bash

# Runs a test program within a new container.  The container is dispatched and/or disposed of, and the exit 
# status code of the target test program collected and returned, by this script.

# The repository containing this harness directory is mapped to a direct subdirectory of / within the container.
# (By present convention that subdirectory is: /prc)  The test program to be run is given by its host path, and
# the internal (to the container) path will be computed.

# The "-L" or  leak option may be given as an instruction not to kill or remove the container after the test run.
# A sourced header for this script, 'test_script_parameters', contains configuration for each script that will
# be run under its control.

KILL_TEST_CONTAINER=1
RUN_AS_USER=""
ECHO_CONTAINER=""
REMOVE_OPTION="--rm"
EXPLICIT_WORKDIR=""
VERBOSITY=0
while [[ $1  = -* ]]; do
    if [ "$1" = -V ]; then
        VERBOSITY=1
        shift
    fi
    if [ "$1" = -c ]; then
        ECHO_CONTAINER=1
        shift
    fi
    if [ "$1" = -L ]; then
        KILL_TEST_CONTAINER=0
        shift
    fi
    if [ "$1" = -u ]; then
        RUN_AS_USER="$2"
        shift 2
    fi
    if [ "$1" = -r ]; then
        REMOVE_OPTION="$2"
        shift 2
    fi
    if [ "$1" = -w ]; then
        EXPLICIT_WORKDIR="$2"
        shift 2
    fi
done

if [ "$1" = "" ]; then
    echo >&2 "Usage: $0 [options] /path/to/script"
    echo >&2 "With options: [-L] to leak, [-u username] to run as non-root user"
    exit 1
fi

DIR=$(dirname "$0")
. "$DIR"/test_script_parameters

testscript=${1}
shift

testscript_basename=$(basename "$testscript")
arglist=${wrapper_arglist[$testscript_basename]:-$*}  # arglist dominated by symbolic link name if any

if [ -L "$testscript" ]; then
    testscript=$(realpath "$testscript")
    testscript_basename=$(basename "$testscript")
fi

original_testscript_abspath=$(realpath "$testscript")

wrapped=${wrappers["$testscript_basename"]}

if [ -n "$wrapped" ]; then
    # wrapped is assumed to contain a leading path element relative to the referencing script's containing directory
    testscript="$(dirname "$testscript")/$wrapped"
    testscript_basename=$(basename "$testscript")
fi

testscript_abspath=$(realpath "$testscript")

cd "$DIR"

image=${images[$testscript_basename]}

if [ -z "$RUN_AS_USER" ]; then
    RUN_AS_USER=${user[$testscript_basename]}
fi

# Tests are run as testuser by default
: ${RUN_AS_USER:='testuser'}

WORKDIR=""
if [ -n "$EXPLICIT_WORKDIR" ]; then
    WORKDIR="$EXPLICIT_WORKDIR"
else
    WORKDIR=${workdirs[$RUN_AS_USER]}
fi

reporoot=$(./print_repo_root_location)
ORIGINAL_SCRIPT_RELATIVE_TO_ROOT=$(realpath --relative-to "$reporoot" "$original_testscript_abspath")

echo "ORIGINAL_SCRIPT_RELATIVE_TO_ROOT=[$ORIGINAL_SCRIPT_RELATIVE_TO_ROOT]"
INNER_MOUNT=/prc

: ${DOCKER:=docker}

# Start the container.
echo image="[$image]"
CONTAINER=$($DOCKER run -d -v "$reporoot:$INNER_MOUNT:ro" $REMOVE_OPTION $image)

# Wait for iRODS and database to start up.
TIME0=$(date +%s)
while :; do
    [ $(date +%s) -gt $((TIME0 + 30)) ] && { echo >&2 "Waited too long for DB and iRODS to start"; exit 124; }
    sleep 1
    $DOCKER exec $CONTAINER grep '(0)' /tmp/irods_status 2>/dev/null >/dev/null
    [ $? -ne 0 ] && { echo -n . >&2; continue; }
    break
done

if [ $VERBOSITY -gt 0 ]; then
    echo $'\n'"==> Running script [$testscript_abspath]"
    echo      "in container [$CONTAINER]"
    echo      "with these *_VERSION variables in environment: "
    $DOCKER exec $CONTAINER bash -c 'env|grep _VERSION' | sed $'s/^/\t/'
fi

$DOCKER exec ${RUN_AS_USER:+"-u$RUN_AS_USER"} \
             ${WORKDIR:+"-w$WORKDIR"} \
	     -e "ORIGINAL_SCRIPT_RELATIVE_TO_ROOT=$ORIGINAL_SCRIPT_RELATIVE_TO_ROOT" \
             $CONTAINER \
             "$INNER_MOUNT/$(realpath --relative-to "$reporoot" "$testscript_abspath")" \
             $arglist
STATUS=$?

if [ $((0+KILL_TEST_CONTAINER)) -ne 0 ]; then
    echo >&2 'Killed:' $($DOCKER stop --timeout=0 $CONTAINER)
fi

[ -n "$ECHO_CONTAINER" ] && echo $CONTAINER
exit $STATUS
