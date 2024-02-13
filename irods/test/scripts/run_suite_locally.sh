#!/usr/bin/env bash
set -e

SCRIPT_DIR=$(dirname "$0")
. "$SCRIPT_DIR"/test_support_functions

run_tests() {
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
  python runner.py --output_tests_skipped /tmp/skipped.txt -e PYTHON_RULE_ENGINE_INSTALLED --tests irods.test.rule_test
  "

  # Install PREP (Python Rule Engine Plugin).
  (
      set -e
      cd "$SCRIPT_DIR/../harness"
      apt update
      ./install_python_rule_engine
      su irods -c './setup_python_rule_engine --wait'
  )

  # Run PREP-dependent tests that were previously skipped.
  su - testuser -c "
  set -e
  source /pyN/bin/activate
  cd /prc.rw/irods/test
  env PYTHON_RULE_ENGINE_INSTALLED=yes python runner.py --tests_file /tmp/skipped.txt
  "
}

run_tests
