#!/bin/bash
. "$(dirname "$0")/scripts/test_support_functions"
. "$(dirname "$0")/scripts/update_json_for_test"

IRODS_SERVER_CONFIG=/etc/irods/server_config.json
IRODS_SERVICE_ACCOUNT_ENV_FILE=~irods/.irods/irods_environment.json
LOCAL_ACCOUNT_ENV_FILE=~/.irods/irods_environment.json

cannot_iinit=''
tries=8
while true; do
    iinit_as_rods >/dev/null 2>&1 && break
    [ $((--tries)) -le 0 ] && {
        cannot_iinit=1
        break
    }
    sleep 5
done
[ -n "$cannot_iinit" ] && {
    echo >&2 "Could not iinit as rods."
    exit 2
}

setup_preconnect_preference DONT_CARE

add_irods_to_system_pam_configuration

# set up /etc/irods/ssl directory and files
set_up_ssl sudo

sudo useradd -ms/bin/bash alissa
sudo chpasswd <<<"alissa:test123"

update_json_file $IRODS_SERVICE_ACCOUNT_ENV_FILE \
    "$(newcontent $IRODS_SERVICE_ACCOUNT_ENV_FILE ssl_keys)"

# This is mostly so we can call python3 as just "python"
activate_virtual_env_with_prc_installed >/dev/null 2>&1 || {
    echo >&2 "couldn't set up virtual environment"
    exit 1
}

server_hup=
if irods_server_version ge 5.0.0; then
    server_hup="y"
    update_json_file $IRODS_SERVER_CONFIG \
        "$(newcontent $IRODS_SERVER_CONFIG tls_server_items tls_client_items)"

    sudo su - irods -c "$IRODS_CONTROL_PATH/manage_irods5_procs rescan-config"
fi

# Configure clients with admin user + TLS

update_json_file $LOCAL_ACCOUNT_ENV_FILE \
    "$(newcontent $LOCAL_ACCOUNT_ENV_FILE ssl_keys encrypt_keys)"

update_time=0
# We won't time out, however we will warn for each minute the server
# has not returned to readiness.
if [ "$server_hup" = "y" ]; then
    # wait for server to be ready after configuration reload
    while true; do
        sleep 2
        if ils >/dev/null 2>&1; then
            break
        else
            now=$(date +%s)
            if [ $now -ge $((update_time + 60)) ]; then
                echo >&2 "At [$(date)] ... still waiting on server reload"
                update_time=$now
            fi
        fi
    done
fi

if [ -n "$ORIGINAL_SCRIPT_RELATIVE_TO_ROOT" ]; then
    original_script="/prc/$ORIGINAL_SCRIPT_RELATIVE_TO_ROOT"

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

fi
