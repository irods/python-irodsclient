#!/usr/bin/env bats
#
# Test creation of .irodsA for iRODS pam_password authentication, this time purely internal to the PRC
# library code.

. "$BATS_TEST_DIRNAME"/test_support_functions
PYTHON=python3

# Setup/prerequisites are same as for login_auth_test.
# Run as ubuntu user with sudo; python_irodsclient must be installed (in either ~/.local or a virtualenv)
#

ALICES_PAM_PASSWORD=test123

setup()
{
    export SKIP_IINIT_FOR_PASSWORD=1
    setup_pam_login_for_alice "$ALICES_PAM_PASSWORD"
    unset SKIP_IINIT_FOR_PASSWORD
}

teardown()
{
:
# finalize_pam_login_for_alice
# test_specific_cleanup
}

@test f001 {

    AUTH_FILE=~/.irods/.irodsA

    # Test assertion: No pre-existing authentication file.
    ! [ -e $AUTH_FILE ]

    local SCRIPT="
import irods.test.helpers as h
ses = h.make_session()
ses.collections.get(h.home_collection(ses))
print ('env_auth_scheme=%s' % ses.pool.account._original_authentication_scheme)
"

    # First invocation.  PRC will both authenticate with pam_password, and write the generated secrets to the auth file,
    OUTPUT=$($PYTHON -c "import irods.client_configuration as cfg
cfg.legacy_auth.pam.password_for_auto_renew = '$ALICES_PAM_PASSWORD'
cfg.legacy_auth.pam.time_to_live_in_hours = 1
cfg.legacy_auth.pam.store_password_to_environment = True
$SCRIPT")

    SECRETS_0=$(cat $AUTH_FILE)
    STAT_0=$(stat -c%y $AUTH_FILE)

    sleep 1.1

    # Second invocation.  PRC will use previously generated secrets from the auth file generated in the first invocation.
    OUTPUT=$($PYTHON -c "import irods.client_configuration as cfg
#cfg.legacy_auth.pam.password_for_auto_renew = '$ALICES_PAM_PASSWORD'
cfg.legacy_auth.pam.time_to_live_in_hours = 1
cfg.legacy_auth.pam.store_password_to_environment = True
$SCRIPT")

    SECRETS_1=$(cat $AUTH_FILE)
    STAT_1=$(stat -c%y $AUTH_FILE)

    # Test assertion: authentication file is the same, before and after, with identical modification date and contents.
    [ "$STAT_1" = "$STAT_0" ]
    [ "$SECRETS_0" = "$SECRETS_1" ]

    # Test assertion: authentication method is pam_password
    [ $OUTPUT = "env_auth_scheme=pam_password" ]
}
