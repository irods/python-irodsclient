#!/usr/bin/env bash
set -e

SCRIPT_DIR=$(dirname "$0")
. "$SCRIPT_DIR"/test_support_functions

report_environment_variables() {
    echo "PRC under test with these environment variables active:"
    python -c "
import os, sys
for name in ['IRODS_PACKAGE_VERSION','PYTHON_VERSION']:
  value = os.environ.get(name)
  print(f'  {name}=[{value}]')
print(f'{sys.executable = }')
print(f'{sys.version = }')
  "
}

run_tests() {
    setup_pyN
    su - testuser -c "
  set -e
  source /pyN/bin/activate
  pip install -e /prc.rw[tests]
  cd /prc.rw/irods/test
  python /prc.rw/test_harness/utility/iinit.py \
    host localhost \
    port 1247 \
    user rods \
    zone tempZone \
    password rods
  $(declare -f report_environment_variables)
  report_environment_variables
  python runner.py --output_tests_skipped /tmp/skipped.txt -e PYTHON_RULE_ENGINE_INSTALLED
  "

    # Install PREP (Python Rule Engine Plugin).
    (
        set -e
        cd "/prc/test_harness/single_node"
        apt update
        ./install_python_rule_engine
        su irods -c './setup_python_rule_engine --wait'
    )

    # Run PREP-dependent tests that were previously skipped.
    su - testuser -c "
  set -e
  source /pyN/bin/activate
  cd /prc.rw/irods/test
  $(declare -f report_environment_variables)
  report_environment_variables
  env PYTHON_RULE_ENGINE_INSTALLED=yes python runner.py --tests_file /tmp/skipped.txt
  "
}

run_tests
