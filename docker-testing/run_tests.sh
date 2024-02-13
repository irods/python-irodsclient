#!/bin/bash
set -e -x
PYTHON=$(which python3)
if [ -z "$PYTHON" ]; then
    PYTHON=$(which python)
fi
DIR=$(dirname "$0")
cd "$DIR"
$PYTHON ./recv_oneshot -h irods-catalog-provider -p 8888 -t 360
REPO="$(./print_repo_root_location)"
$PYTHON -m pip install "$REPO[tests]"

if [ -d /irods_shared ]; then
    groupadd -o -g $(stat -c%g /irods_shared) irods      # Appropriate the integer codes for irods group ...
    useradd -g irods -u $(stat -c%u /irods_shared) irods # ... and user.
    mkdir /irods_shared/{tmp,reg_resc}
    chown irods.irods /irods_shared/{tmp,reg_resc}
    chmod 777 /irods_shared/reg_resc
    chmod g+ws /irods_shared/tmp
    useradd -G irods -m -s/bin/bash user
fi

su - user -c "\
$PYTHON '$DIR'/iinit.py \
    host irods-catalog-provider \
    port 1247 \
    user rods \
    password rods \
    zone tempZone
$PYTHON '$REPO'/irods/test/runner.py $*"
