#! /bin/bash -e

catalog_db_hostname=irods-catalog

echo "Waiting for iRODS catalog database to be ready"

until pg_isready -h ${catalog_db_hostname} -d ICAT -U irods -q
do
    sleep 1
done

echo "iRODS catalog database is ready"

setup_input_file=/irods_setup.input

if [ -e "${setup_input_file}" ]; then
    echo "Running iRODS setup"
    python3 /var/lib/irods/scripts/setup_irods.py < "${setup_input_file}"
    rm /irods_setup.input
fi

ORIG_SERVER_CONFIG=/etc/irods/server_config.json
MOD_SERVER_CONFIG=/tmp/server_config.json.$$

#TODO ensure this is done for 4.3+ only. 4.2 doesn't have this server config key
{
    [ -f ~/provider-address.do_not_remove ] || {
    jq <$ORIG_SERVER_CONFIG >$MOD_SERVER_CONFIG \
    '.host_resolution.host_entries += [
        {
            "address_type": "local",
            "addresses": [
                "irods-catalog-provider",
                "'$(hostname)'"
            ]
        }
    ]' && \
    cat <$MOD_SERVER_CONFIG >$ORIG_SERVER_CONFIG && \
    touch ~/provider-address.do_not_remove 
    }
} || { echo >&2 "Error modifying $ORIG_SERVER_CONFIG"; exit 1; }

echo "Starting server"

# After successful launch of server (per ils success), signal the client container we are ready
{
    # wait until server is up
    while :; do
        su - irods -c ils >/dev/null 2>&1 && break
        #echo "** waiting on server before send_oneshot" |tee -a /tmp/debug.dan 
        sleep 1
    done
    chown -R irods:irods /irods_shared
    echo "**** got this far - about to execute send_oneshot" |tee -a /tmp/debug.dan 
    env PORT=8888 "$(dirname "$0")"/send_oneshot
} &

cd /usr/sbin
su irods -c 'bash -c "./irodsServer -u"'

