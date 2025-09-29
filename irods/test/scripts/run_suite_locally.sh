#!/usr/bin/env bash

setup() {
  set -e
  if [ ! -d  /pyN ]; then
    mkdir /pyN ; chown testuser /pyN
    su - testuser -c "/root/python/bin/python3 -m virtualenv /pyN"
    cp -r /prc{,.rw}
    chown -R testuser /prc.rw
  fi
}

test() {
  setup
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
  python runner.py
  "
}

test
