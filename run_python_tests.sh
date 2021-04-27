#!/bin/bash

set -o pipefail
cd repo/irods/test 

export PYTHONUNBUFFERED="Y"

if [ -z "${TESTS_TO_RUN}" ] ; then
    python${PY_N} runner.py 2>&1 | tee ${LOG_OUTPUT_DIR}/prc_test_logs.txt
else 
    python${PY_N} -m unittest -v ${TESTS_TO_RUN} 2>&1 | tee ${LOG_OUTPUT_DIR}/prc_test_logs.txt
fi

