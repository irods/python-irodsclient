#!/bin/bash
set -e

# This script is launched on the docker host.

usage() {
  echo >&2 "usage: $0 [irods_version] python_version"; exit 1;
}

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

IRODS_MAJOR=${IRODS_VERSION//.*/}

# In case the docker-compose setup varies between iRODS major releases, the .YML file may be a symbolic link.

docker compose -f harness-docker-compose-irods-${IRODS_MAJOR}.yml down
