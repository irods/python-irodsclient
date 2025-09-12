#!/bin/bash
set -e
IRODS_VERSION=$1
PYTHON_VERSION=$2
shift 2
[ -n "$PYTHON_VERSION" -a -n "$IRODS_VERSION" ] || {
  echo >&2 "usage: $0 irods_version python_version"; exit 1; 
}
IRODS_MAJOR=$(sed -e 's/\..*//' <<<"$IRODS_VERSION")

DIR=$(dirname "$0")
cd "${DIR}"

echo "\
python_version=${PYTHON_VERSION}
irods_version=${IRODS_VERSION}" >.env

docker compose -f harness-docker-compose-irods-${IRODS_MAJOR}.yml build $*
docker compose -f harness-docker-compose-irods-${IRODS_MAJOR}.yml up -d
