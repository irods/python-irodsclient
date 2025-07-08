#!/usr/bin/env bats

. "$BATS_TEST_DIRNAME"/../setup_pam_and_ssl.funcs

setup() {
  echo setup >>/tmp/log
  setup_preconnect_preference DONT_CARE
  python3 "$BATS_TEST_DIRNAME"/repo/irods/test/setupssl.py
:
}

teardown() {
  echo teardown >>/tmp/log
:
}

@test mytest {
  grep acPreConn /etc/irods/core.re >>/tmp/log
  echo test proper >>/tmp/log
:
}
