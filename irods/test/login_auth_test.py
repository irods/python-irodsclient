#! /usr/bin/env python
from __future__ import print_function
from __future__ import absolute_import
import os
import sys
import tempfile
import unittest
import textwrap
import json
import shutil
import ssl
import irods.test.helpers as helpers
from irods.connection import Connection
from irods.session import iRODSSession, NonAnonymousLoginWithoutPassword
from irods.rule import Rule
from irods.models import User
from socket import gethostname
from irods.password_obfuscation import (encode as pw_encode)
from irods.connection import PlainTextPAMPasswordError
from irods.access import iRODSAccess
import irods.exception as ex
import contextlib
import socket
from re import compile as regex
import gc
import six

try:
    from re import _pattern_type as regex_type
except ImportError:
    from re import Pattern as regex_type  # Python 3.7+


def json_file_update(fname,keys_to_delete=(),**kw):
    with open(fname,'r') as f:
        j = json.load(f)
    j.update(**kw)
    for k in keys_to_delete:
        if k in j: del j [k]
        elif isinstance(k,regex_type):
            jk = [i for i in j.keys() if k.search(i)]
            for ky in jk: del j[ky]
    with open(fname,'w') as out:
        json.dump(j, out, indent=4)

def env_dir_fullpath(authtype):  return os.path.join( os.environ['HOME'] , '.irods.' + authtype)
def json_env_fullpath(authtype):  return os.path.join( env_dir_fullpath(authtype), 'irods_environment.json')
def secrets_fullpath(authtype):   return os.path.join( env_dir_fullpath(authtype), '.irodsA')

SERVER_ENV_PATH = os.path.expanduser('~irods/.irods/irods_environment.json')

SERVER_ENV_SSL_SETTINGS = {
    "irods_ssl_certificate_chain_file": "/etc/irods/ssl/irods.crt",
    "irods_ssl_certificate_key_file": "/etc/irods/ssl/irods.key",
    "irods_ssl_dh_params_file": "/etc/irods/ssl/dhparams.pem",
    "irods_ssl_ca_certificate_file": "/etc/irods/ssl/irods.crt",
    "irods_ssl_verify_server": "cert"
}

def update_service_account_for_SSL():
    json_file_update( SERVER_ENV_PATH, **SERVER_ENV_SSL_SETTINGS )

CLIENT_OPTIONS_FOR_SSL = {
    "irods_client_server_policy": "CS_NEG_REQUIRE",
    "irods_client_server_negotiation": "request_server_negotiation",
    "irods_ssl_ca_certificate_file": "/etc/irods/ssl/irods.crt",
    "irods_ssl_verify_server": "cert",
    "irods_encryption_key_size": 16,
    "irods_encryption_salt_size": 8,
    "irods_encryption_num_hash_rounds": 16,
    "irods_encryption_algorithm": "AES-256-CBC"
}


def client_env_from_server_env(user_name, auth_scheme=""):
    cli_env = {}
    with open(SERVER_ENV_PATH) as f:
        srv_env = json.load(f)
        for k in [ "irods_host", "irods_zone_name", "irods_port"  ]:
            cli_env [k] = srv_env[k]
    cli_env["irods_user_name"] = user_name
    if auth_scheme:
        cli_env["irods_authentication_scheme"] = auth_scheme
    return cli_env

@contextlib.contextmanager
def pam_password_in_plaintext(allow=True):
    saved = bool(Connection.DISALLOWING_PAM_PLAINTEXT)
    try:
        Connection.DISALLOWING_PAM_PLAINTEXT = not(allow)
        yield
    finally:
        Connection.DISALLOWING_PAM_PLAINTEXT = saved


class TestLogins(unittest.TestCase):
    '''
    Ideally, these tests should move into CI, but that would require the server
    (currently a different node than the client) to have SSL certs created and
    enabled.

    Until then, we require these tests to be run manually on a server node,
    with:

        python -m unittest "irods.test.login_auth_test[.XX[.YY]]'

    Additionally:

      1. The PAM/SSL tests under the TestLogins class should be run on a
         single-node iRODS system, by the service account user. This ensures
         the /etc/irods directory is local and writable.

      2. ./setupssl.py (sets up SSL keys etc. in /etc/irods/ssl) should be run
         first to create (or overwrite, if appropriate) the /etc/irods/ssl directory
         and its contents.

      3. Must add & override configuration entries in /var/lib/irods/irods_environment
         Per https://slides.com/irods/ugm2018-ssl-and-pam-configuration#/3/7

      4. Create rodsuser alissa and corresponding unix user with the appropriate
         passwords as below.
    '''

    test_rods_user = 'alissa'

    user_auth_envs = {
        '.irods.pam': {
            'USER':     test_rods_user,
            'PASSWORD': 'test123', # UNIX pw
            'AUTH':     'pam'
        },
        '.irods.native': {
            'USER':     test_rods_user,
            'PASSWORD': 'apass',   # iRODS pw
            'AUTH':     'native'
        }
    }

    env_save = {}

    @contextlib.contextmanager
    def setenv(self,var,newvalue):
        try:
            self.env_save[var] = os.environ.get(var,None)
            os.environ[var] = newvalue
            yield newvalue
        finally:
            oldvalue = self.env_save[var]
            if oldvalue is None:
                del os.environ[var]
            else:
                os.environ[var]=oldvalue

    @classmethod
    def create_env_dirs(cls):
        dirs = {}
        retval = []
        # -- create environment configurations and secrets
        with pam_password_in_plaintext():
            for dirname,lookup in cls.user_auth_envs.items():
                if lookup['AUTH'] == 'pam':
                    ses = iRODSSession( host=gethostname(),
                                        user=lookup['USER'],
                                        zone='tempZone',
                                        authentication_scheme=lookup['AUTH'],
                                        password=lookup['PASSWORD'],
                                        port= 1247 )
                    try:
                        pam_hashes = ses.pam_pw_negotiated
                    except AttributeError:
                        pam_hashes = []
                    if not pam_hashes: print('Warning ** PAM pw couldnt be generated' ); break
                    scrambled_pw = pw_encode( pam_hashes[0] )
               #elif lookup['AUTH'] == 'XXXXXX': # TODO: insert other authentication schemes here
                elif lookup['AUTH'] in ('native', '',None):
                    scrambled_pw = pw_encode( lookup['PASSWORD'] )
                cl_env = client_env_from_server_env(cls.test_rods_user)
                if lookup.get('AUTH',None) is not None:     # - specify auth scheme only if given
                    cl_env['irods_authentication_scheme'] = lookup['AUTH']
                dirbase = os.path.join(os.environ['HOME'],dirname)
                dirs[dirbase] = { 'secrets':scrambled_pw , 'client_environment':cl_env }

        # -- create the environment directories and write into them the configurations just created
        for absdir in dirs.keys():
            shutil.rmtree(absdir,ignore_errors=True)
            os.mkdir(absdir)
            with open(os.path.join(absdir,'irods_environment.json'),'w') as envfile:
                envfile.write('{}')
            json_file_update(envfile.name, **dirs[absdir]['client_environment'])
            with open(os.path.join(absdir,'.irodsA'),'w') as secrets_file:
                secrets_file.write(dirs[absdir]['secrets'])
            os.chmod(secrets_file.name,0o600)

        retval = dirs.keys()
        return retval


    @staticmethod
    def get_server_ssl_negotiation( session ):

        rule_body = textwrap.dedent('''
                                    test { *out=""; acPreConnect(*out);
                                               writeLine("stdout", "*out");
                                         }
                                    ''')
        myrule = Rule(session, body=rule_body, params={}, output='ruleExecOut')
        out_array = myrule.execute()
        buf = out_array.MsParam_PI[0].inOutStruct.stdoutBuf.buf.decode('utf-8')
        eol_offset = buf.find('\n')
        return  buf[:eol_offset]  if  eol_offset >= 0  else None

    @classmethod
    def setUpClass(cls):
        cls.admin = helpers.make_session()
        if cls.test_rods_user in (row[User.name] for row in cls.admin.query(User.name)):
            cls.server_ssl_setting = cls.get_server_ssl_negotiation( cls.admin )
            cls.envdirs = cls.create_env_dirs()
            if not cls.envdirs:
                raise RuntimeError('Could not create one or more client environments')

    @classmethod
    def tearDownClass(cls):
        for envdir in getattr(cls, 'envdirs', []):
            shutil.rmtree(envdir, ignore_errors=True)
        cls.admin.cleanup()

    def setUp(self):
        if not getattr(self, 'envdirs', []):
            self.skipTest('The test_rods_user "{}" does not exist'.format(self.test_rods_user))
        if os.environ['HOME'] != '/var/lib/irods':
            self.skipTest('Must be run as irods')
        super(TestLogins,self).setUp()

    def tearDown(self):
        super(TestLogins,self).tearDown()

    def validate_session(self, session, verbose=False, **options):
        
        # - try to get the home collection
        home_coll =  '/{0.zone}/home/{0.username}'.format(session)
        self.assertTrue(session.collections.get(home_coll).path == home_coll)
        if verbose: print(home_coll)
        # - check user is as expected
        self.assertEqual( session.username, self.test_rods_user )
        # - check socket type (normal vs SSL) against whether ssl requested
        use_ssl = options.pop('ssl',None)
        if use_ssl is not None:
            my_connect = [s for s in (session.pool.active|session.pool.idle)] [0]
            self.assertEqual( bool( use_ssl ), my_connect.socket.__class__ is ssl.SSLSocket )


#   def test_demo(self): self.demo()

#   def demo(self): # for future reference - skipping based on CS_NEG_DONT_CARE setting
#       if self.server_ssl_setting == 'CS_NEG_DONT_CARE':
#           self.skipTest('skipping  b/c setting is DONT_CARE')
#       self.assertTrue (False)


    def tst0(self, ssl_opt, auth_opt, env_opt ):
        auth_opt_explicit = 'native' if auth_opt=='' else  auth_opt
        verbosity=False
        #verbosity='' # -- debug - sanity check by printing out options applied
        out = {'':''}
        if env_opt:
            with self.setenv('IRODS_ENVIRONMENT_FILE', json_env_fullpath(auth_opt_explicit)) as env_file,\
                 self.setenv('IRODS_AUTHENTICATION_FILE', secrets_fullpath(auth_opt_explicit)):
                cli_env_extras = {} if not(ssl_opt) else dict( CLIENT_OPTIONS_FOR_SSL )
                if auth_opt:
                    cli_env_extras.update( irods_authentication_scheme = auth_opt )
                    remove=[]
                else:
                    remove=[regex('authentication_')]
                with helpers.file_backed_up(env_file):
                    json_file_update( env_file, keys_to_delete=remove, **cli_env_extras )
                    session = iRODSSession(irods_env_file=env_file)
                    with open(env_file) as f:
                        out =  json.load(f)
                    self.validate_session( session, verbose = verbosity, ssl = ssl_opt )
                    session.cleanup()
            out['ARGS']='no'
        else:
            session_options = {}
            if auth_opt:
                session_options.update (authentication_scheme = auth_opt)
            if ssl_opt:
                SSL_cert = CLIENT_OPTIONS_FOR_SSL["irods_ssl_ca_certificate_file"]
                session_options.update(
                    ssl_context = ssl.create_default_context ( purpose = ssl.Purpose.SERVER_AUTH,
                                                               capath = None,
                                                               cadata = None,
                                                               cafile = SSL_cert),
                    **CLIENT_OPTIONS_FOR_SSL )
            lookup = self.user_auth_envs ['.irods.'+('native' if not(auth_opt) else auth_opt)]
            session = iRODSSession ( host=gethostname(),
                                     user=lookup['USER'],
                                     zone='tempZone',
                                     password=lookup['PASSWORD'],
                                     port= 1247,
                                     **session_options )
            out = session_options
            self.validate_session( session, verbose = verbosity, ssl = ssl_opt )
            session.cleanup()
            out['ARGS']='yes'

        if verbosity == '':
            print ('--- ssl:',ssl_opt,'/ auth:',repr(auth_opt),'/ env:',env_opt)
            print ('--- > ',json.dumps({k:v for k,v in out.items() if k != 'ssl_context'},indent=4))
            print ('---')

    # == test defaulting to 'native'

    def test_01(self):
        self.tst0 ( ssl_opt = True , auth_opt = '' , env_opt = False )
    def test_02(self):
        self.tst0 ( ssl_opt = False, auth_opt = '' , env_opt = False )
    def test_03(self):
        self.tst0 ( ssl_opt = True , auth_opt = '' , env_opt = True )
    def test_04(self):
        self.tst0 ( ssl_opt = False, auth_opt = '' , env_opt = True  )

    # == test explicit scheme 'native'

    def test_1(self):
        self.tst0 ( ssl_opt = True , auth_opt = 'native' , env_opt = False )

    def test_2(self):
        self.tst0 ( ssl_opt = False, auth_opt = 'native' , env_opt = False )

    def test_3(self):
        self.tst0 ( ssl_opt = True , auth_opt = 'native' , env_opt = True )

    def test_4(self):
        self.tst0 ( ssl_opt = False, auth_opt = 'native' , env_opt = True  )

    # == test explicit scheme 'pam'

    def test_5(self):
        self.tst0 ( ssl_opt = True,  auth_opt = 'pam'    , env_opt = False )

    def test_6(self):
        try:
            self.tst0 ( ssl_opt = False, auth_opt = 'pam'    , env_opt = False )
        except PlainTextPAMPasswordError:
            pass
        else:
            # -- no exception raised
            self.fail("PlainTextPAMPasswordError should have been raised")

    def test_7(self):
        self.tst0 ( ssl_opt = True , auth_opt = 'pam'    , env_opt = True  )

    def test_8(self):
        self.tst0 ( ssl_opt = False, auth_opt = 'pam'    , env_opt = True  )

class TestAnonymousUser(unittest.TestCase):

    def setUp(self):
        admin = self.admin = helpers.make_session()

        user = self.user = admin.users.create('anonymous', 'rodsuser', admin.zone)
        self.home = '/{admin.zone}/home/{user.name}'.format(**locals())

        admin.collections.create(self.home)
        acl = iRODSAccess('own', self.home, user.name)
        admin.permissions.set(acl)

        self.env_file = os.path.expanduser('~/.irods.anon/irods_environment.json')
        self.env_dir = ( os.path.dirname(self.env_file))
        self.auth_file = os.path.expanduser('~/.irods.anon/.irodsA')
        os.mkdir( os.path.dirname(self.env_file))
        json.dump( { "irods_host": admin.host,
                     "irods_port": admin.port,
                     "irods_user_name": user.name,
                     "irods_zone_name": admin.zone }, open(self.env_file,'w'), indent=4 )

    def tearDown(self):
        self.admin.collections.remove(self.home, recurse = True, force = True)
        self.admin.users.remove(self.user.name)
        shutil.rmtree (self.env_dir, ignore_errors = True)

    def test_login_from_environment(self):
        orig_env = os.environ.copy()
        try:
            os.environ["IRODS_ENVIRONMENT_FILE"] = self.env_file
            os.environ["IRODS_AUTHENTICATION_FILE"] = self.auth_file
            ses = helpers.make_session()
            ses.collections.get(self.home)
        finally:
            os.environ.clear()
            os.environ.update( orig_env )

class TestMiscellaneous(unittest.TestCase):

    def test_nonanonymous_login_without_auth_file_fails__290(self):
        ses = self.admin
        if ses.users.get( ses.username ).type != 'rodsadmin':
            self.skipTest( 'Only a rodsadmin may run this test.')
        try:
            ENV_DIR = tempfile.mkdtemp()
            ses.users.create('bob', 'rodsuser')
            ses.users.modify('bob', 'password', 'bpass')
            d = dict(password = 'bpass', user = 'bob', host = ses.host, port = ses.port, zone = ses.zone)
            (bob_env, bob_auth) = helpers.make_environment_and_auth_files(ENV_DIR, **d)
            login_options = { 'irods_env_file': bob_env, 'irods_authentication_file': bob_auth }
            with helpers.make_session(**login_options) as s:
                s.users.get('bob')
            os.unlink(bob_auth)
            # -- Check that we raise an appropriate exception pointing to the missing auth file path --
            with self.assertRaisesRegexp(NonAnonymousLoginWithoutPassword, bob_auth):
                with helpers.make_session(**login_options) as s:
                    s.users.get('bob')
        finally:
            try:
                shutil.rmtree(ENV_DIR,ignore_errors=True)
                ses.users.get('bob').remove()
            except ex.UserDoesNotExist:
                pass


    def setUp(self):
        admin = self.admin = helpers.make_session()
        if admin.users.get(admin.username).type != 'rodsadmin':
            self.skipTest('need admin privilege')
        admin.users.create('alice','rodsuser')

    def tearDown(self):
        self.admin.users.remove('alice')
        self.admin.cleanup()

    @unittest.skipUnless(six.PY3, "Skipping in Python2 because it doesn't reliably do cyclic GC.")
    def test_destruct_session_with_no_pool_315(self):

        destruct_flag = [False]

        class mySess( iRODSSession ):
            def __del__(self):
                self.pool = None
                super(mySess,self).__del__()  # call parent destructor(s) - will raise
                                              # an error before the #315 fix
                destruct_flag[:] = [True]

        admin = self.admin
        admin.users.modify('alice','password','apass')

        my_sess = mySess( user = 'alice',
                          password = 'apass',
                          host = admin.host,
                          port = admin.port,
                          zone = admin.zone)
        my_sess.cleanup()
        del my_sess
        gc.collect()
        self.assertEqual( destruct_flag, [True] )

    def test_non_anon_native_login_omitting_password_fails_1__290(self):
        # rodsuser with password unset
        with self.assertRaises(ex.CAT_INVALID_USER):
            self._non_anon_native_login_omitting_password_fails_N__290()

    def test_non_anon_native_login_omitting_password_fails_2__290(self):
        # rodsuser with a password set
        self.admin.users.modify('alice','password','apass')
        with self.assertRaises(ex.CAT_INVALID_AUTHENTICATION):
            self._non_anon_native_login_omitting_password_fails_N__290()

    def _non_anon_native_login_omitting_password_fails_N__290(self):
        admin = self.admin
        with iRODSSession(zone = admin.zone, port = admin.port, host = admin.host, user = 'alice') as alice:
            alice.collections.get(helpers.home_collection(alice))

class TestWithSSL(unittest.TestCase):
    '''
    The tests within this class should be run by an account other than the
    service account.  Otherwise there is risk of corrupting the server setup.
    '''

    def setUp(self):
        if os.path.expanduser('~') == '/var/lib/irods':
            self.skipTest('TestWithSSL may not be run by user irods')
        if not os.path.exists('/etc/irods/ssl'):
            self.skipTest('Running setupssl.py as irods user is prerequisite for this test.')
        with helpers.make_session() as session:
            if not session.host in ('localhost', socket.gethostname()):
                self.skipTest('Test must be run co-resident with server')


    def test_ssl_with_server_verify_set_to_none_281(self):
        env_file = os.path.expanduser('~/.irods/irods_environment.json')
        with helpers.file_backed_up(env_file):
            with open(env_file) as env_file_handle:
                env = json.load( env_file_handle )
            env.update({ "irods_client_server_negotiation": "request_server_negotiation",
                         "irods_client_server_policy": "CS_NEG_REQUIRE",
                         "irods_ssl_ca_certificate_file": "/path/to/some/file.crt",  # does not need to exist
                         "irods_ssl_verify_server": "none",
                         "irods_encryption_key_size": 32,
                         "irods_encryption_salt_size": 8,
                         "irods_encryption_num_hash_rounds": 16,
                         "irods_encryption_algorithm": "AES-256-CBC" })
            with open(env_file,'w') as f:
                json.dump(env,f)
            with helpers.make_session() as session:
                session.collections.get('/{session.zone}/home/{session.username}'.format(**locals()))


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
