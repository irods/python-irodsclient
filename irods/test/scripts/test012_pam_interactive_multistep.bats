#!/usr/bin/env bats

# The tests in this BATS module must be run as a (passwordless) sudo-enabled user.
# It is also required that the python irodsclient be installed under irods' ~/.local environment.

SKIP_IINIT_FOR_PASSWORD=yes

. $BATS_TEST_DIRNAME/test_support_functions

export TESTUSER="john"
export FIRST_PASSWORD="=i;r@o\\d&s" # somerods
export SECOND_PASSWORD="otherrods"
export CLIENT_AUTH_ERROR_EXITCODE=123

ssl_hash() {
  openssl passwd -6 "$1"
}

setup() {
  [ -f /tmp/test012_flag ] || {
      rm -fr ~/.irods
      /prc/test_harness/utility/iinit.py host localhost \
          port 1247     \
          zone tempZone \
          user rods     \
          password rods \

      sudo apt update
      sudo apt install -y db-util libpam0g-dev jq

      ## Because iRODS 5+ negotiates for SSL automatically:
      CLIENT_JSON=~/.irods/irods_environment.json
      jq '.irods_client_server_policy="CS_NEG_REFUSE"' >$CLIENT_JSON.$$ <$CLIENT_JSON && \
      mv  $CLIENT_JSON.$$ $CLIENT_JSON

      # if plugin installation would upgrade server, then skip test.
      if irods_server_package_upgradable; then
          skip
      fi

      sudo apt install -y irods-auth-plugin-pam-interactive-{client,server}
      SERVER_CONFIG=server_config.json

      sudo -s <<-EOF
	jq '.plugin_configuration.authentication.pam_interactive = {
	    "pam_stack_name": "pam_interactive"
	}' <"/etc/irods/${SERVER_CONFIG}" >"/tmp/${SERVER_CONFIG}"
	cp -rp "/etc/irods/${SERVER_CONFIG}"{,.orig}
	mv -f "/tmp/${SERVER_CONFIG}" "/etc/irods/${SERVER_CONFIG}"
	EOF
      waitsrv() {
          while true; do
              sleep 5
              ils >& /dev/null && break
          done
      }

      { sudo kill -HUP `sudo cat /tmp/irods.pid` && waitsrv; } || {
         echo "Couldn't properly bounce server after configuration change."; exit 1; }

      setup_pam_login_for_user "${FIRST_PASSWORD}" $TESTUSER
      sudo cp $BATS_TEST_DIRNAME/files_for_test012/pam_password    /etc/pam.d/irods
      sudo cp $BATS_TEST_DIRNAME/files_for_test012/pam_interactive /etc/pam.d/
      sudo mkdir /t012 && sudo gcc -o /t012/pam_clear_token.so -fno-stack-protector -shared -fPIC $BATS_TEST_DIRNAME/files_for_test012/pam_clear_token.c

      ## Switch over to scheme to be tested.
      jq '.irods_authentication_scheme="pam_interactive"' >$CLIENT_JSON.$$ <$CLIENT_JSON && \
      mv  $CLIENT_JSON.$$ $CLIENT_JSON
  }
  touch /tmp/test012_flag

  # Tests require only the irods_environment.json
  rm -f ~/.irods/.irodsA
}

encode_2nd_password() {
      db_file=/t012/pam_userdb.db
      sudo db_load -T -t hash "$db_file" <<<"${TESTUSER}"$'\n'"$(ssl_hash ${1})"
      sudo chown root:root "$db_file"
      sudo chmod 600 "$db_file"
}

SCRIPT="
import getpass
import os

import irods
from irods.auth import  ClientAuthError
from unittest.mock import patch

def getpass_new_callable(answers=()):
    class iterate_answers:
        def __init__(self,answers = answers):
            self.answers = answers
            self.count = 0
        def __call__(self,*_):
            count = self.count
            self.count += 1
            ans = self.answers[count]
            print ('*** giving answer:', ans)
            return ans
    return lambda : iterate_answers()

home = None

pw_count = 0

with patch(
    'getpass.getpass',
    new_callable=getpass_new_callable(answers=[os.environ['FIRST_PASSWORD'],os.environ['SECOND_PASSWORD']])
) as m:
    try:
        sess = irods.helpers.make_session(test_server_version=False)
        sess.set_auth_option_for_scheme('pam_interactive', irods.auth.FORCE_PASSWORD_PROMPT, True)
        home = sess.collections.get(f'/{sess.zone}/home/{sess.username}')
    except ClientAuthError as exc:
        # Note:  The write to stdout, and the specific exit code, are necessary for the test assertions.
        # in test "pam_interactive_test_multistep_with_incorrect_2nd_password" below.
        print(f'ERROR: {exc!r}')
        exit(int(os.environ['CLIENT_AUTH_ERROR_EXITCODE']))
    finally:
        pw_count = m.count

# Assert both passwords were prompted for.
if pw_count < 2:
    print(f'************************ {pw_count = } < 2')
    exit(3)

# Assert home is defined, ie a session was successfully created and used to retrieve a collection object
if home is None:
    exit(2)

username = os.environ['TESTUSER']

# Assert home contains the expected username.
if not home.path.endswith(f'/{username}'):
    exit(1)
"

@test "pam_interactive_test_multistep_with_incorrect_2nd_password" {

    # We are using a deliberately munged password.
    encode_2nd_password "_${SECOND_PASSWORD}"
    local STATUS=""
    OUTPUT=$(python -c "$SCRIPT" 2>&1) || STATUS=$?

    # Here, we assert the process's exit and output conform to expectation. We want to
    # enforce that the stdout output stream contains the thrown exception name ("ClientAuthError")
    # as well as that the process exits with a particular error status.
    [ $STATUS = $CLIENT_AUTH_ERROR_EXITCODE ]
    [[ $OUTPUT =~ ClientAuthError ]]
}

@test "pam_interactive_test_multistep_with_correct_2nd_password" {
    encode_2nd_password "${SECOND_PASSWORD}"
    python -c "$SCRIPT"
}
