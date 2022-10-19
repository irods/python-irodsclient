#!/usr/bin/env bats

# Run with
#   * $RUN containing a unique string
#   * $REPO pointing to this repository
#   For example, in Bash:
#   $ REPO=~/relative/path/python-irodsclient RUN=$$:`date +%s` bats test_ssl_context.bats
#   (This allows us to perform the one-time initialization before test cases are run.)
#
# Note also:
#
# This series of tests should be run by a Linux user (not root, and not the iRODS service
# account i.e. irods) iinit'ed as rods in a default iRODS server installation.
#
# That user's home directory, the python-irodsclient repository, and all intervening
# path elements need to be visible to the irods user (a concern on Centos 7).
#
# The bats package must be installed to run this test script.
#
# The c_rehash binary is also needed (provided by the openssl package on Debian-like and
# openssl-perl on RHEL-like operating systems.)

# iRODS RELATED INITIALIZATION

IRODS_LOCAL_ENV=~/.irods/irods_environment.json
IRODS_ACCOUNT_ENV=~irods/.irods/irods_environment.json

edit_core_re () {
    if [ "$1" = ssl ]; then
        sudo su irods -c "sed -i.orig 's/\(^\s*acPreConnect.*CS_NEG\)\([A-Z_]*\)/\1_REQUIRE/' /etc/irods/core.re"
    else
        if [ -f /etc/irods/core.re.orig ]; then
            sudo su irods -c "cp -rp /etc/irods/core.re.orig /etc/irods/core.re"
        else
            echo >&2 "Warning - could not restore original core.re"
        fi
    fi
}

restart_server()
{
    sudo su irods -c '~/irodsctl restart'
}

if [ "$LOGFILE" = "<syslog>" ]; then
    log () { logger "`date`: $*"; } 		# Log to (r)syslog
elif [ -n "$LOGFILE" ]; then
    log () { echo "`date`: $*" >>"$LOGFILE" ; }	# Log to a file.
else
    log () { :; }			 		# NOP
fi

: ${REPO:=~/python-irodsclient}
REPO_SCRIPTS="$REPO/irods/test"
PATH=$REPO_SCRIPTS:$PATH

ABBREVIATIONS=(
        VAR='irods_ssl_*ca_certificate_file'
        VAR='irods_ssl_*ca_certificate_path'
        VAR='irods_ssl_*verify_server'
        VAR='irods_ssl_*dh_params_file'
        VAR='irods_ssl_*certificate_key_file'
        VAR='irods_ssl_*certificate_chain_file'
        VAR='irods_*encryption_algorithm'
        VAR='irods_*encryption_key_size'
        VAR='irods_*encryption_num_hash_rounds'
        VAR='irods_*encryption_salt_size'
        VAR='irods_*client_server_policy'
        VAR='irods_*client_server_negotiation'
)

touch /tmp/run
if [ "`cat /tmp/run`" != "$RUN" ]; then

    ## -- Begin one-time initialization --

    #  Initialize the variable abbreviations
    json_config --clear-store ${ABBREVIATIONS[*]}
    # The next two lines were necessary under Centos 7. sudo behaved differently wrt
    # what is considered the home directory, so the wrong ~/.store* file was being used.
    sudo su irods -c "$REPO_SCRIPTS/json_config --clear-store ${ABBREVIATIONS[*]}"
    sudo $REPO_SCRIPTS/json_config --clear-store ${ABBREVIATIONS[*]}

    # Set up the basic server cert, key, and DH params file.
    [ -e /etc/irods/ssl ] || sudo su irods -c "$REPO_SCRIPTS/setupssl.py -f"

    # Set up another cert with non-matching hostname.
    sudo su irods -c "$REPO_SCRIPTS/setupssl.py -kf -x.localhost -hlocalhost"
    sudo su irods -c "c_rehash /etc/irods/ssl"

    # Change the iRODS svc account user's (and current user's) iRODS environment file for SSL.
    sudo $REPO_SCRIPTS/json_config -i $IRODS_ACCOUNT_ENV\
        'client_server_policy="CS_NEG_REQUIRE"'\
        'ca_certificate_file="/etc/irods/ssl/irods.crt"'\
        'certificate_key_file="/etc/irods/ssl/irods.key"'\
        'dh_params_file="/etc/irods/ssl/dhparams.pem"'\
        'certificate_chain_file="/etc/irods/ssl/irods.crt"'\
        'verify_server="cert"'
    json_config -i $IRODS_LOCAL_ENV\
        'client_server_negotiation="request_server_negotiation"'\
        'encryption_algorithm="AES-256-CBC"'\
        'encryption_key_size=32'\
        'encryption_num_hash_rounds=16'\
        'encryption_salt_size=8'\
        'client_server_policy="CS_NEG_REQUIRE"'\
        'verify_server="cert"'\
        'ca_certificate_file="/etc/irods/ssl/irods.crt"'

    # Set the SSL-reconfigured environment files as (PRESERVE/RESTORE) checkpoints
    # to be managed by setup and teardown.
    sudo $REPO_SCRIPTS/json_config -i $IRODS_ACCOUNT_ENV -i $IRODS_LOCAL_ENV PRESERVE

    restart_server

    edit_core_re ssl

    # In case of things falling down prematurely, set things back to a stable state.
    # This is an unconditional and one-time finalization that runs regardless, after all tests
    # or in case of something catastrophic such as being killed by a signal.)
    trap 'log "Tests Finalizing..."
          sudo $REPO_SCRIPTS/json_config -i $IRODS_ACCOUNT_ENV -i $IRODS_LOCAL_ENV RESTORE
          edit_core_re RESTORE
    ' exit
    #
    ## --  End one-time init  --
    echo "$RUN" >/tmp/run
fi

# TEST-RELATED SETUP & TEARDOWN

setup() {
    log "[$BATS_TEST_NAME] - setup"
    # Make sure we're back to the configuration checkpoint.
    sudo $REPO_SCRIPTS/json_config -i "$IRODS_ACCOUNT_ENV" -i "$IRODS_LOCAL_ENV" PRESERVE_check
}

teardown() {
    log "[$BATS_TEST_NAME] - teardown"
    # Restore to the configuration checkpoint.
    sudo $REPO_SCRIPTS/json_config -i "$IRODS_ACCOUNT_ENV" -i "$IRODS_LOCAL_ENV" RESTORE
}

# THE TESTS THEMSELVES

@test "basic_test" {
    json_config -i $IRODS_LOCAL_ENV 'verify_server="host"'
    python3 $REPO_SCRIPTS/ssl_test_client.py
}

@test "capath_test" {
    json_config -i $IRODS_LOCAL_ENV 'ca_certificate_path="/etc/irods/ssl"'\
                                     'ca_certificate_file='
    python3 $REPO_SCRIPTS/ssl_test_client.py
}

@test "nocerts_test" {
    json_config -i $IRODS_LOCAL_ENV 'ca_certificate_path='\
                                    'ca_certificate_file='\
                                    'verify_server="none"'
    python3 $REPO_SCRIPTS/ssl_test_client.py
}

@test "non_matching_hostname_test" {
    local CERT_NOT_MATCHING_HOSTNAME=/etc/irods/ssl/irods.crt.localhost
    sudo $REPO_SCRIPTS/json_config -i $IRODS_LOCAL_ENV $IRODS_ACCOUNT_ENV\
                                    'verify_server="cert"'\
                                    "ca_certificate_file='$CERT_NOT_MATCHING_HOSTNAME'"
    sudo $REPO_SCRIPTS/json_config -i $IRODS_ACCOUNT_ENV\
                                    "certificate_chain_file='$CERT_NOT_MATCHING_HOSTNAME'"
    restart_server
    python3 $REPO_SCRIPTS/ssl_test_client.py
}
