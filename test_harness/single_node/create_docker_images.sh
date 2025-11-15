#!/bin/bash

export IRODS_PACKAGE_VERSION=$1
export PYTHON_VERSION=$2

[ -z "$1" -o -z "$2" ] && {
    echo >&2 "usage: $0 <irods-version> <python-version>"
    exit 2
}
shift 2

DIR=$(dirname "$0")

"$DIR"/build-docker.sh $*
