#!/usr/bin/env bats
#
# Test creation of .irodsA for iRODS native authentication using the free function,
#    irods.client_init.write_native_credentials_to_secrets_file

. "$BATS_TEST_DIRNAME"/test_support_functions
PYTHON=python3

# Setup/prerequisites are same as for login_auth_test.
# Run as ubuntu user with sudo; python_irodsclient must be installed (in either ~/.local or a virtualenv)
#

@test create_irods_secrets_file {

    rm -fr ~/.irods
    mkdir ~/.irods
    cat > ~/.irods/irods_environment.json <<-EOF
	{ "irods_host":"$(hostname)",
	  "irods_port":1247,
	  "irods_user_name":"rods",
	  "irods_zone_name":"tempZone"
	}
	EOF
    $PYTHON -c "import irods.client_init; irods.client_init.write_native_irodsA_file('rods')"

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
    [ $OUTPUT = "env_auth_scheme=native" ]

    # New starting point with no .irodsA, assert iCommands not working
    rm -fr ~/.irods/.irodsA
    if ! ils 2>/tmp/stderr ; then
        true
    else
        echo 2>/tmp/stderr "ils should fail when no .irodsA is present"
        exit 2
    fi

    # Write another .irodsA
    prc_write_irodsA.py native <<<"rods"

    # Verify new .irodsA for both iCommands and PRC use.
    ils >/tmp/stdout
    OUTPUT=$($PYTHON -c "$SCRIPT")
    [ $OUTPUT = "env_auth_scheme=native" ]

}
