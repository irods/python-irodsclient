#!/bin/bash
set -e

# This script is launched on the docker host.

usage() {
  echo >&2 "usage: $0 irods_version python_version"; exit 1;
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

REPO_ROOT=$(realpath ..)

shift 2
[ -n "$PYTHON_VERSION" -a -n "$IRODS_VERSION" ] || {
     usage
}
IRODS_MAJOR=$(sed -e 's/\..*//' <<<"$IRODS_VERSION")

DIR=$(dirname "$0")
cd "${DIR}"

echo "\
repo_external=\"${REPO_ROOT}\"
python_version=\"${PYTHON_VERSION}\"
irods_version=\"${IRODS_VERSION}\"
irods_major=\"${IRODS_MAJOR}\"" >.env

docker compose -f harness-docker-compose-irods-${IRODS_MAJOR}.yml build $*
docker compose -f harness-docker-compose-irods-${IRODS_MAJOR}.yml up -d
