#!/usr/bin/env bats
#
# Test creation of .irodsA for iRODS pam_password authentication using the free function,
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

@test main {
    auth_file=~/.irods/.irodsA

    CONTENTS1=$(cat $auth_file)

    # Alter the pam password.
    sudo chpasswd <<<"alice:$ALICES_NEW_PAM_PASSWD"
    OUTPUT=$($PYTHON -c "import irods.client_init;
try:
    irods.client_init.write_pam_irodsA_file('$ALICES_NEW_PAM_PASSWD', overwrite = False)
except irods.client_init.irodsA_already_exists:
    print ('CANNOT OVERWRITE')
")
    [ "$OUTPUT" = "CANNOT OVERWRITE" ]
    # Assert the previous contents of irodsA have not changed, and aren't zero length.
    CONTENTS2=$(cat $auth_file)
    [ -n "$CONTENTS1" -a "$CONTENTS1" = "$CONTENTS2" ]

    # Now delete the already existing irodsA and repeat without negating overwrite.
    $PYTHON -c "import irods.client_init; irods.client_init.write_pam_irodsA_file('$ALICES_NEW_PAM_PASSWD')"
    CONTENTS3=$(cat $auth_file)
    [ "$CONTENTS2" != "$CONTENTS3" ]

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
    [[ $OUTPUT = "env_auth_scheme=pam"* ]]

}
