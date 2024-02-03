#!/usr/bin/env bats
#
# Test creation of .irodsA for iRODS native authentication using the free function,
#    irods.client_init.write_pam_credentials_to_secrets_file

. "$BATS_TEST_DIRNAME"/test_support_functions
PYTHON=python3

# Setup/prerequisites are same as for login_auth_test.
# Run as ubuntu user with sudo; python_irodsclient must be installed (in either ~/.local or a virtualenv)
#

ALICES_OLD_PAM_PASSWD="test123"
ALICES_NEW_PAM_PASSWD="new_pass"

setup()
{
    setup_pam_login_for_alice "$ALICES_OLD_PAM_PASSWD"
}

teardown()
{
    finalize_pam_login_for_alice
    test_specific_cleanup
}

@test create_secrets_file {

    # Old .irodsA is already created, so we delete it and alter the pam password.
    sudo chpasswd <<<"alice:$ALICES_NEW_PAM_PASSWD"
    rm -f ~/.irods/.irodsA
    $PYTHON -c "import irods.client_init; irods.client_init.write_pam_credentials_to_secrets_file('$ALICES_NEW_PAM_PASSWD')"

    # Define the core Python to be run, basically a minimal code block ensuring that we can authenticate to iRODS
    # without an exception being raised.

    local SCRIPT="
import irods.test.helpers as h
ses = h.make_session()
ses.collections.get(h.home_collection(ses))
print ('env_auth_scheme=%s' % ses.pool.account._original_authentication_scheme)
"
    OUTPUT=$($PYTHON -c "$SCRIPT")
    # Assert passing value
    [ $OUTPUT = "env_auth_scheme=pam_password" ]

}
