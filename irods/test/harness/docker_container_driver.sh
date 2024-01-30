#!/usr/bin/env bash

KILL_TEST_CONTAINER=1
RUN_AS_USER=""
ECHO_CONTAINER=""

EXPLICIT_WORKDIR=""
while [[ $1  = -* ]]; do
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

DIR=$(dirname $0)
. "$DIR"/test_script_parameters

testscript=${1}

testscript_basename=$(basename "$testscript")
arglist=${wrapper_arglist[$testscript_basename]}  # arglist dominated by symbolic link name if any

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
ORIGINAL_SCRIPT_RELATIVE_TO_ROOT=$(realpath --relative-to $reporoot "$original_testscript_abspath")

echo "ORIGINAL_SCRIPT_RELATIVE_TO_ROOT=[$ORIGINAL_SCRIPT_RELATIVE_TO_ROOT]" 
INNER_MOUNT=/prc

# Start the container.
echo image="[$image]"
CONTAINER=$(docker run -d -v $reporoot:$INNER_MOUNT:ro --rm $image)

# Wait for iRODS and database to start up.
TIME0=$(date +%s)
while :; do
    [ `date +%s` -gt $((TIME0 + 30)) ] && { echo >&2 "Waited too long for DB and iRODS to start"; exit 124; }
    sleep 1 
    docker exec $CONTAINER grep '(0)' /tmp/irods_status 2>/dev/null >/dev/null
    [ $? -ne 0 ] && { echo -n . >&2; continue; }
    break
done

docker exec ${RUN_AS_USER:+"-u$RUN_AS_USER"} \
            ${WORKDIR:+"-w$WORKDIR"} \
	    -e "ORIGINAL_SCRIPT_RELATIVE_TO_ROOT=$ORIGINAL_SCRIPT_RELATIVE_TO_ROOT" \
            $CONTAINER \
            $INNER_MOUNT/$(realpath --relative-to $reporoot "$testscript_abspath") \
            $arglist
STATUS=$?

if [ $((0+KILL_TEST_CONTAINER)) -ne 0 ]; then
    echo >&2 'Killed:' $(docker stop --time=0 $CONTAINER)
fi

[ -n "$ECHO_CONTAINER" ] && echo $CONTAINER
exit $STATUS
