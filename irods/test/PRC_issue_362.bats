# The tests in this BATS module must be run as a (passwordless) sudo-enabled user.
# It is also required that the python irodsclient be installed under irods' ~/.local environment.


setup() {
  local -A chars=(
    [semicolon]=";"
    [atsymbol]="@"
    [equals]="="
    [ampersand]="&"
  )
  [ $BATS_TEST_NUMBER = 1 ] && echo "---" >/tmp/PRC_test_issue_362
  local name=${BATS_TEST_DESCRIPTION##*_}
  CHR="${chars[$name]}"
}

TEST_THE_TEST=""

prc_test()
{
  local USER="alissa"
  local PASSWORD=$(tr "." "$CHR" <<<"my.pass")
  echo "$USER:$PASSWORD" | sudo chpasswd
  if [ "$TEST_THE_TEST" = 1 ]; then
    echo -n `date`: "" >&2
    { su - "$USER" -c "id" <<<"$PASSWORD" 2>/dev/null | grep $USER ; } >&2
  else
    sudo su - irods -c "env PYTHON_IRODSCLIENT_TEST_PAM_PW_OVERRIDE='$PASSWORD' python -m unittest \
                        irods.test.login_auth_test.TestLogins.test_escaped_pam_password_chars__362"
  fi
} 2>> /tmp/PRC_test_issue_362

@test "test_with_atsymbol"	{ prc_test; }
@test "test_with_semicolon"	{ prc_test; }
@test "test_with_equals"	{ prc_test; }
@test "test_with_ampersand"	{ prc_test; }
