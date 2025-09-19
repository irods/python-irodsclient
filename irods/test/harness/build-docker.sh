#!/usr/bin/env bash

# environment variables for build
# IRODS_PACKAGE_VERSION if defined is like "4.3.4" or "5.0.1".
# (but contains no '~' suffix for irods versions <= 4.2.10)
# PYTHON_VERSION is usually two dot-separated numbers: example "3.13", but could also have zero, one or three version numbers.
# (Do not specify the triple form, X.Y.Z, if that release is not known to exist - not counting alphas and release candidates)

BASE=$(basename "$0")
DIR=$(realpath "$(dirname "$0")")
cd "$DIR"
: ${DOCKER:=docker}
if [ $# -gt 0 ]; then
    ARGS=("$@")
else
    ARGS=([0-9]*.Dockerfile)
fi
for dockerfile in "${ARGS[@]}"; do 
    image_name=${dockerfile#[0-9]*_}
    image_name=${image_name%.Dockerfile}
    irods_package_version_option=""
    python_version_option=""
    if [ "$image_name" = "install-irods" ]; then
        irods_package_version_option=${IRODS_PACKAGE_VERSION:+"--build-arg=irods_package_version=$IRODS_PACKAGE_VERSION"}
    elif [ "$image_name" = "compile-specific-python" ]; then
        temp=$(./most_recent_python.sh $PYTHON_VERSION)
        if [ -n "$temp" ]; then
            PYTHON_VERSION="$temp"
        fi
        python_version_option=${PYTHON_VERSION:+"--build-arg=python_version=$PYTHON_VERSION"}
    else
        package_version_option=""
    fi
    $DOCKER build -f $dockerfile -t $image_name . $irods_package_version_option $python_version_option \
                                                  ${NO_CACHE+"--no-cache"} || 
                                                  { STATUS=$?; echo "*** Failure while building [$image_name]"; exit $STATUS; }
done
