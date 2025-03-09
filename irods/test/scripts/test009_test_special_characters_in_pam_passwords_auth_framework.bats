#!/usr/bin/env bats

# Test creation and use of PAM password authentication info in .irodsA when the password itself contains
# special characters (those known to have created issues in the past).

. "$BATS_TEST_DIRNAME"/test_support_functions
PYTHON=python3

# Setup/prerequisites are same as for login_auth_test.
# Run as ubuntu user with sudo; python_irodsclient must be installed (in either ~/.local or a virtualenv)

ALICES_NEW_PAM_PASSWD="new_&@;=_pass"

setup()
{
    export SKIP_IINIT_FOR_PASSWORD=1
    setup_pam_login_for_alice "$ALICES_OLD_PAM_PASSWD"
    unset SKIP_IINIT_FOR_PASSWORD
}

teardown()
{
    finalize_pam_login_for_alice
    test_specific_cleanup
}

@test main {
    irods_server_version ge 4.3.0 || {
       skip "Requires at least iRODS server 4.3.0"
       return
    }
    # Old .irodsA is already created, so we delete it and alter the pam password.
    sudo chpasswd <<<"alice:$ALICES_NEW_PAM_PASSWD"
    prc_write_irodsA.py pam_password <<<"$ALICES_NEW_PAM_PASSWD"

    local SCRIPT="
import irods.test.helpers as h
ses = h.make_session()
ses.collections.get(h.home_collection(ses))
print ('env_auth_scheme=%s' % ses.pool.account._original_authentication_scheme)
"
    OUTPUT=$($PYTHON -c "$SCRIPT")
    # Assert passing value
    [[ $OUTPUT = "env_auth_scheme=pam_password" ]]
}
