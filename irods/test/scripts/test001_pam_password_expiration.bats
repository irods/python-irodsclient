#!/usr/bin/env bats

. "$BATS_TEST_DIRNAME"/test_support_functions
PYTHON=python3

# Setup/prerequisites are same as for login_auth_test.
# Run as ubuntu user with sudo; python_irodsclient must be installed (in either ~/.local or a virtualenv)
#

ALICES_PAM_PASSWORD=test123

setup()
{
    setup_pam_login_for_alice $ALICES_PAM_PASSWORD
}

teardown()
{
    finalize_pam_login_for_alice
    test_specific_cleanup
}

@test main {

    # Define the core Python to be run, basically a minimal code block ensuring that we can authenticate to iRODS
    # without an exception being raised.

    local SCRIPT="
import irods.test.helpers as h
ses = h.make_session()
ses.collections.get(h.home_collection(ses))
print ('env_auth_scheme=%s' % ses.pool.account._original_authentication_scheme)
"

    # Test that the first run of the code in $SCRIPT is successful, i.e. normal authenticated operations are possible.

    local OUTPUT=$($PYTHON -c "$SCRIPT")

    [[ $OUTPUT = "env_auth_scheme=pam"* ]]

    age_out_pam_password "alice"

    HOME_COLLECTION=$(ipwd)
    OUTPUT=$($PYTHON -c "$SCRIPT" 2>&1 >/dev/null || true)
    grep 'CAT_PASSWORD_EXPIRED' <<<"$OUTPUT"

    # Test that the $SCRIPT, when run in legacy auth mode and with proper settings, can successfully reset the password.

    OUTPUT=$($PYTHON -c "import irods.client_configuration as cfg
cfg.legacy_auth.force_legacy_auth = True
cfg.legacy_auth.pam.password_for_auto_renew = '$ALICES_PAM_PASSWORD'
cfg.legacy_auth.pam.time_to_live_in_hours = 1
cfg.legacy_auth.pam.store_password_to_environment = True
$SCRIPT")

    [[ $OUTPUT = "env_auth_scheme=pam"* ]]

    # Test that iCommands can authenticate with the newly written .irodsA file

    iquest "%s" "select COLL_NAME where COLL_NAME like '%/home/alice%'"| grep "^$HOME_COLLECTION\$"
}
