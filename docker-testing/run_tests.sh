#!/bin/bash
set -e -x
PYTHON=$(which python3)
if [ -z "$PYTHON" ]; then
    PYTHON=$(which python)
fi
DIR=$(dirname "$0")
cd "$DIR"

REPO="$(./print_repo_root_location)"

if [ -d /irods_shared ]; then

    # Get the numeric user and group id's for irods service account on the provider.  This helps to set up the test user
    # (named 'user') with proper permissions for the shared volume on the client node.
    groupadd -o -g $(stat -c%g /irods_shared) irods
    useradd -g irods -u $(stat -c%u /irods_shared) irods

    # Set up useful subdirectories in the client/provider shared volume.
    mkdir /irods_shared/{tmp,reg_resc}
    chown irods:irods /irods_shared/{tmp,reg_resc}
    chmod 777 /irods_shared/reg_resc
    chmod g+ws /irods_shared/tmp

    # Make a test user in group irods, who will run the client tests.
    useradd -G irods -m -s/bin/bash user

    # Create writable copy of this repo.
    cp -r /"$REPO"{,.copy}
    REPO+=.copy
    chown -R user "$REPO"
    chmod u+w "$REPO"/irods/test/test-data

    # Install PRC from the repo.
    $PYTHON -m pip install "$REPO[tests]"
fi

su - user -c "\
$PYTHON '$DIR'/iinit.py \
    host irods-catalog-provider \
    port 1247 \
    user rods \
    password rods \
    zone tempZone
$PYTHON '$REPO'/irods/test/runner.py $*"
