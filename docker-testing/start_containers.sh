#!/bin/bash
PYTHON_VERSION=$1
shift
[ -n "$PYTHON_VERSION" ] || { echo >&2 "requires python_version as argument"; exit 1; }
set -e
DIR=$(dirname "$0")
cd "${DIR}"
echo "python_version=${PYTHON_VERSION}" >.env
echo "repo_external=$(./print_repo_root_location)" >>.env
echo "parent_pid=$$" >>.env

docker compose -f harness-docker-compose.yml build $*
docker compose -f harness-docker-compose.yml up -d
