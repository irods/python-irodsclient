#!/usr/bin/env -S bats --verbose-run

setup() {
  true
}

@test main {
  echo 1
  sleep 1
  echo 2
  sleep 1
  echo 3
}
