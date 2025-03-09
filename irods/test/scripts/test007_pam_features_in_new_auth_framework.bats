#!/usr/bin/env bats
#
# Test creation of .irodsA for iRODS pam_password authentication, this time purely internal to the PRC
# library code.

. "$BATS_TEST_DIRNAME"/test_support_functions
PYTHON=python3

# Setup/prerequisites are same as for login_auth_test.
# Run as ubuntu user with sudo; python_irodsclient must be installed (in either ~/.local or a virtualenv)
#

ALICES_ORIGINAL_PAM_PASSWORD=test123
ALICES_NEW_PASSWORD=test_1234

setup()
{
    export SKIP_IINIT_FOR_PASSWORD=1
    setup_pam_login_for_alice "$ALICES_ORIGINAL_PAM_PASSWORD"
    unset SKIP_IINIT_FOR_PASSWORD
}

teardown()
{
    finalize_pam_login_for_alice
    test_specific_cleanup
}

@test main {

    local AUTH_FILE=~/.irods/.irodsA

    # Test assertion: No pre-existing authentication file.
    [ ! -e $AUTH_FILE ]

    python -c "import sys, irods.client_init; \
               pw=sys.stdin.readline().strip(); irods.client_init.write_pam_irodsA_file(pw)" \
              <<<"$ALICES_ORIGINAL_PAM_PASSWORD"
    [ -e $AUTH_FILE ]

    # ===  test we can log in.

    local SCRIPT="
import irods.test.helpers as h
ses = h.make_session()
try:
  ses.collections.get(h.home_collection(ses))
except:
  print('authenticate error.')
  exit(120)
print ('env_auth_scheme=%s' % ses.pool.account._original_authentication_scheme)
"
    # Test Python script authenticates.
    OUTPUT=$($PYTHON -c "$SCRIPT")
    [[ $OUTPUT = "env_auth_scheme=pam"* ]]

    mc1=$(mtime_and_content $AUTH_FILE)
    sleep 2

    # ===  test we can log in with direct way, not relying on client environment.
    SCRIPT_DIRECT="import irods.helpers, irods.session
SSL_OPTIONS = {
    'irods_client_server_policy': 'CS_NEG_REQUIRE',
    'irods_client_server_negotiation': 'request_server_negotiation',
    'irods_ssl_ca_certificate_file': '/etc/irods/ssl/irods.crt',
    'irods_ssl_verify_server': 'cert',
    'irods_encryption_key_size': 16,
    'irods_encryption_salt_size': 8,
    'irods_encryption_num_hash_rounds': 16,
    'irods_encryption_algorithm': 'AES-256-CBC'
}
ses = irods.session.iRODSSession(user = 'alice', password = '$ALICES_ORIGINAL_PAM_PASSWORD',
                                 host = 'localhost', port = 1247, zone = 'tempZone',
                                 authentication_scheme = 'pam_password', **SSL_OPTIONS)
ses.collections.get(irods.helpers.home_collection(ses))
print ('env_auth_scheme=%s' % ses.pool.account._original_authentication_scheme)"

    OUTPUT=$($PYTHON -c "$SCRIPT_DIRECT")
    [[ $OUTPUT = "env_auth_scheme=pam"* ]]

    # Ensure .irodsA has not been touched by authentication with inline parameter-passing.
    mc2=$(mtime_and_content $AUTH_FILE)

    [ "$mc1" == "$mc2" ]

    # Set a new password for alice and use prc_write_irodsA script to alter with chosen
    # time-to-live setting of 2000 seconds.
    sudo chpasswd <<< "alice:$ALICES_NEW_PASSWORD"
    prc_write_irodsA.py -i - --ttl=1 pam_password <<<"$ALICES_NEW_PASSWORD"

    # Check we're able to login with the new password and correspondingly new .irodsA
    OUTPUT=$($PYTHON -c "$SCRIPT")
    [[ $OUTPUT = "env_auth_scheme=pam"* ]]

    age_out_pam_password alice 2000

    OUTPUT=$($PYTHON -c "$SCRIPT")
    [[ $OUTPUT = "env_auth_scheme=pam"* ]]

    # Check that pam password expires after the specified interval is exhausted.
    age_out_pam_password alice 2000
    if ! ils 2>/tmp/stderr ; then grep CAT_PASSWORD_EXPIRED /tmp/stderr ; fi

    # -- Test --ttl option and prc_write_irodsA.py in the pam_password scheme.
    prc_write_irodsA.py --ttl=120 pam_password <<<"$ALICES_NEW_PASSWORD"
    age_out_pam_password alice $((119*3600))
    OUTPUT=$($PYTHON -c "$SCRIPT")
    [[ $OUTPUT = "env_auth_scheme=pam"* ]]
    age_out_pam_password alice $((2*3600))
    OUTPUT=$($PYTHON -c "$SCRIPT" 2>&1 || :)
}
