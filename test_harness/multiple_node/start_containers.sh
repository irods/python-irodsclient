#!/bin/bash
set -e

# This script is launched on the docker host.

usage() {
    echo >&2 "usage: $0 [-n] [-b '<docker compose build args>'] irods_version python_version"
    exit 2
}

SHELL_DOCKER_COMPOSE_BUILD_ARGS=""
DO_NOT_RUN=""

while [[ $1 = -* ]]; do
    if [ "$1" = "-b" ]; then
        SHELL_DOCKER_COMPOSE_BUILD_ARGS=$2
        shift 2
    fi
    if [ "$1" = "-n" ]; then
        DO_NOT_RUN=1
        shift
    fi
done

if [ $# -eq 2 ]; then
    IRODS_VERSION=$1
    PYTHON_VERSION=$2
    shift 2
else
    usage
fi

[ -n "$PYTHON_VERSION" -a -n "$IRODS_VERSION" ] || {
    usage
}

IRODS_MAJOR=${IRODS_VERSION//.*/}

DIR=$(dirname "$0")
cd "${DIR}"
REPO_ROOT=$(realpath ../..)

echo "\
repo_external=\"${REPO_ROOT}\"
python_version=\"${PYTHON_VERSION}\"
irods_version=\"${IRODS_VERSION}\"
irods_major=\"${IRODS_MAJOR}\"" >.env

docker compose -f harness-docker-compose-irods-${IRODS_MAJOR}.yml build $SHELL_DOCKER_COMPOSE_BUILD_ARGS

if [ -z "$DO_NOT_RUN" ]; then
    docker compose -f harness-docker-compose-irods-${IRODS_MAJOR}.yml up -d
fi
