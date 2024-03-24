# The tests in this BATS module must be run as a (passwordless) sudo-enabled user.
# It is also required that the python irodsclient be installed under irods' ~/.local environment.

. $BATS_TEST_DIRNAME/scripts/funcs

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

  ## Arrange for secrets file to be generated internally by the Python client
  cat >~/.python_irodsclient <<-EOF
	legacy_auth.pam.store_password_to_environment True
	legacy_auth.pam.password_for_auto_renew 'my${CHR}pass'
	legacy_auth.pam.time_to_live_in_hours 1
	EOF

  iinit_as_rods

  if [ ! -e /tmp/rodsuser_alissa_created ]; then
      iadmin mkuser alissa rodsuser
  fi
  touch /tmp/rodsuser_alissa_created

  _begin_pam_environment_and_password "" alissa
  rm -f ~/.irods/.irodsA

  cat >~/test_get_home_coll.py <<-EOF
	import irods.test.helpers as h
	ses = h.make_session()
	home_coll = h.home_collection(ses)
	exit(0 if ses.collections.get(home_coll).path == home_coll
	       and ses.pool.account._original_authentication_scheme.lower().startswith('pam')
	     else 1)
	EOF
}

prc_test()
{
  local USER="alissa"
  local PASSWORD="my${CHR}pass"
  sudo chpasswd <<<"$USER:$PASSWORD"
  env PYTHON_IRODSCLIENT_CONFIGURATION_PATH='' python ~/test_get_home_coll.py
}

@test "test_with_atsymbol" { prc_test; }
@test "test_with_semicolon" { prc_test; }
@test "test_with_equals" { prc_test; }
@test "test_with_ampersand" { prc_test; }
