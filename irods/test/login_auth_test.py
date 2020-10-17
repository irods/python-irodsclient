#! /usr/bin/env python
from __future__ import print_function
from __future__ import absolute_import
import os
import sys
import unittest
import textwrap
import json
import shutil
import ssl
import irods.test.helpers as helpers
from irods.connection import Connection
from irods.session import iRODSSession
from irods.rule import Rule
from irods.models import User
from socket import gethostname
from irods.password_obfuscation import (encode as pw_encode)
from irods.connection import PlainTextPAMPasswordError
import contextlib
from re import compile as regex
try:
    from re import _pattern_type as regex_type
except ImportError:
    from re import Pattern as regex_type  # Python 3.7+


def json_file_update(fname,keys_to_delete=(),**kw):
    j = json.load(open(fname,'r'))
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
    This is due to be moved into Jenkins CI along core and other iRODS tests.
    Until  then, for these tests to run successfully, we require:
      1. First run ./setupssl.py (sets up SSL keys etc. in /etc/irods/ssl)
      2. Add & override configuration entries in /var/lib/irods/irods_environment
         Per https://slides.com/irods/ugm2018-ssl-and-pam-configuration#/3/7
      3. Create rodsuser alissa and corresponding unix user with the appropriate
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
            with open(os.path.join(absdir,'.irodsA'),'wb') as secrets_file:
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
                    out =  json.load(open(env_file))
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


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
