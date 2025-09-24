#!/bin/bash

export IRODS_PACKAGE_VERSION=$1
export PYTHON_VERSION=$2

DIR=$(dirname "$0")

"$DIR"/build-docker.sh
