#!/bin/bash
set -e

# This script is launched on the docker host.

usage() {
  echo >&2 "usage: $0 [-b "<docker compose build args>"] irods_version python_version"; exit 1;
}

SHELL_DOCKER_COMPOSE_BUILD_ARGS=""

if [ $1 = "-b" ]
then
    SHELL_DOCKER_COMPOSE_BUILD_ARGS=$2
    shift 2
fi

if [ $# -eq 2 ]; then
    IRODS_VERSION=$1
    PYTHON_VERSION=$2
elif [ $# -eq 1 ]; then
    IRODS_VERSION=4.3.4
    PYTHON_VERSION=$1
else
    usage
fi

shift $#

[ -n "$PYTHON_VERSION" -a -n "$IRODS_VERSION" ] || {
     usage
}

IRODS_MAJOR=$(sed -e 's/\..*//' <<<"$IRODS_VERSION")

DIR=$(dirname "$0")
cd "${DIR}"
REPO_ROOT=$(realpath ..)

echo "\
repo_external=\"${REPO_ROOT}\"
python_version=\"${PYTHON_VERSION}\"
irods_version=\"${IRODS_VERSION}\"
irods_major=\"${IRODS_MAJOR}\"" >.env

docker compose -f harness-docker-compose-irods-${IRODS_MAJOR}.yml build $SHELL_DOCKER_COMPOSE_BUILD_ARGS
##dwm
#docker compose -f harness-docker-compose-irods-${IRODS_MAJOR}.yml up -d
