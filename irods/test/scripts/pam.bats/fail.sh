#!/bin/bash

DIR=$(dirname $0)
. $DIR/funcs
cd "$DIR"; echo >&2 -n -- ; pwd
#echo "setting up"
$(up_from_script_dir 1)/demo_script
#set_up_ssl sudo
id -un
exit 12
