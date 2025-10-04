#!/bin/bash
DIR=$(dirname $0)
. $DIR/test_support_functions
cd "$DIR"
set_up_ssl sudo
add_irods_to_system_pam_configuration
