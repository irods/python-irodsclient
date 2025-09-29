#!/usr/bin/env bash
set -e

. "$(dirname "$0")"/test_support_functions

test() {
  setup_pyN
  su - testuser -c "
  set -e
  source /pyN/bin/activate
  pip install -e /prc.rw[tests]
  cd /prc.rw/irods/test
  python /prc.rw/docker-testing/iinit.py \
    host localhost \
    port 1247 \
    user rods \
    zone tempZone \
    password rods
  echo ; echo 'PRC under test: === iRODS [$IRODS_PACKAGE_VERSION] ; Python [$PYTHON_VERSION]'
  python runner.py
  "
}

test
