#!/bin/bash
. $(dirname $0)/scripts/funcs
. $(dirname $0)/scripts/update_json_for_test

IRODS_SERVICE_ACCOUNT_ENV_FILE=~irods/.irods/irods_environment.json 
LOCAL_ACCOUNT_ENV_FILE=~/.irods/irods_environment.json 

setup_preconnect_preference DONT_CARE

add_irods_to_system_pam_configuration

# set up /etc/irods/ssl directory and files
set_up_ssl sudo -q

sudo useradd -ms/bin/bash alissa 
sudo chpasswd <<<"alissa:test123"

update_json_file $IRODS_SERVICE_ACCOUNT_ENV_FILE \
                 "$(newcontent $IRODS_SERVICE_ACCOUNT_ENV_FILE ssl_keys)"

# This is mostly so we can call python3 as just "python"
activate_virtual_env_with_prc_installed >/dev/null 2>&1 || { echo >&2 "couldn't set up virtual environment"; exit 1; }

# Set up testuser with rods+SSL so we never have to run login_auth_tests.py as the service account.
iinit_as_rods >/dev/null 2>&1 || { echo >&2 "couldn't iinit as rods"; exit 2; }
update_json_file $LOCAL_ACCOUNT_ENV_FILE \
                 "$(newcontent $LOCAL_ACCOUNT_ENV_FILE ssl_keys encrypt_keys)"

original_script=/prc/$ORIGINAL_SCRIPT_RELATIVE_TO_ROOT
# Run tests.
if [ -x "$original_script" ]; then 
  command "$original_script" $*
elif [[ $original_script =~ \.py$ ]]; then
  python "$original_script" $*
elif [[ $original_script =~ \.bats$ ]]; then
  bats "$original_script"
else
  echo >&2 "I don't know how to run this: original_script=[$original_script]"
fi
