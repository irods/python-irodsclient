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
    setup_pam_login_for_alice "$ALICES_PAM_PASSWORD"
}

teardown()
{

    finalize_pam_login_for_alice
    test_specific_cleanup
}

@test main {

    # Create and put into iRODS a large file which will take a significant fraction of a
    # second (>1e-5 on any CPU + Network combination) to checksum.

    export LARGE_FILE=/tmp/largefile
    export LARGE_FILE_BASENAME=$(basename "$LARGE_FILE")
    dd if=/dev/zero count=150k bs=1k of=$LARGE_FILE
    cat >/tmp/test_script <<-EOF
	import ssl
	from irods.helpers import make_session, home_collection
	
	def check_all_sockets_are_ssl():
	    if {type(conn.socket) for conn in ses.pool.idle | ses.pool.active} != {ssl.SSLSocket}:
	        print('not all sockets are SSL')
	        exit(1)
	ses = make_session()
	
	coll = home_collection(ses)
	ses.data_objects.put('$LARGE_FILE', coll)
	
	check_all_sockets_are_ssl()
	
        # Set timeout too low for chksum reaction time.
	ses.connection_timeout = 1e-5
	
	path1 = coll+'/$LARGE_FILE_BASENAME'
	path2 = coll+'/$LARGE_FILE_BASENAME'+'2'
	try:
	    ses.data_objects.chksum(path1)
	except Exception as e:
	    print(type(e), 'thrown')

        # Set timeout high enough for any reaction time.
	ses.connection_timeout = None

	ses.data_objects.copy(path1, path2)
	with ses.data_objects.open(path2,'a') as object:
	    object.write(b'\0')
	x = ses.data_objects.chksum(path2)
	check_all_sockets_are_ssl()
	EOF

    OUTPUT=$(python /tmp/test_script 2>/tmp/test_stderr | tee /tmp/test_stdout)

    [[ $OUTPUT =~ NetworkException.*thrown$ ]]
}
