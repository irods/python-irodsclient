#!/usr/bin/env bash
run() {
  echo dir of this = $(realpath "$(dirname "${BASH_SOURCE[0]}")/repo")
}

echo hello_there
