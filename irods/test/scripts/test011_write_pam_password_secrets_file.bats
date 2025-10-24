#!/usr/bin/env bats

# The tests in this BATS module must be run as a (passwordless) sudo-enabled user.
# It is also required that the python irodsclient be installed under irods' ~/.local environment.

. $BATS_TEST_DIRNAME/test_support_functions

# Setup in the wrapper script (../login_auth_test.sh) includes creation of Linux user alissa with login password test123 .

@test "test_writing_secrets" {
  iadmin mkuser alissa rodsuser

  # Make a new environment and pam_password secrets file for iRODS user alissa.
  rm -fr .irods/.irodsA
  CLIENT_JSON=~/.irods/irods_environment.json
  jq '.["irods_user_name"]="alissa"|.["irods_authentication_scheme"]="pam_password"' >$CLIENT_JSON.$$ <$CLIENT_JSON
  mv  $CLIENT_JSON.$$ $CLIENT_JSON
  /pyN/bin/prc_write_irodsA.py --ttl 10 pam_password <<<"test123"

  # Test that iCommands pam_password auth works with the secrets file.
  ils </dev/null | grep '/alissa\>'

  # Test that python irods client pam_password authentication works with the secrets file.
  python -c 'import irods.helpers as h; ses=h.make_session(); c=h.home_collection(ses); print(ses.collections.get(c).path)'|\
      grep '/alissa\>'
}
