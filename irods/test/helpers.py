from __future__ import absolute_import
import os
import io
import tempfile
import contextlib
import shutil
import hashlib
import base64
import math
import socket
import inspect
import threading
import random
import datetime
import json
from pwd import getpwnam
from irods.session import iRODSSession
from irods.message import iRODSMessage
from irods.password_obfuscation import encode
from six.moves import range


def my_function_name():
    """Returns the name of the calling function or method"""
    return inspect.getframeinfo(inspect.currentframe().f_back).function


_thrlocal = threading.local()

def unique_name(*seed_tuple):
    '''For deterministic pseudo-random identifiers based on function/method name
       to prevent e.g.  ICAT collisions within and between tests.  Example use:

           def f(session):
             seq_num = 1
             a_name = unique_name( my_function_name(), seq_num # [, *optional_further_args]
                                  )
             seq_num += 1
             session.resources.create( a_name, 'unixfilesystem', session.host, '/tmp/' + a_name )
    '''
    if not getattr(_thrlocal,"rand_gen",None) : _thrlocal.rand_gen = random.Random()
    _thrlocal.rand_gen.seed(seed_tuple)
    return '%016X' % _thrlocal.rand_gen.randint(0,(1<<64)-1)


IRODS_SHARED_DIR = os.path.join( os.path.sep, 'irods_shared' )
IRODS_SHARED_TMP_DIR = os.path.join(IRODS_SHARED_DIR,'tmp')
IRODS_SHARED_REG_RESC_VAULT = os.path.join(IRODS_SHARED_DIR,'reg_resc')

IRODS_REG_RESC = 'MyRegResc'

def irods_shared_tmp_dir():
    pth = IRODS_SHARED_TMP_DIR
    can_write = False
    if os.path.exists(pth):
        try:     tempfile.NamedTemporaryFile(dir = pth)
        except:  pass
        else:    can_write = True 
    return pth if can_write else ''

def irods_shared_reg_resc_vault() :
    vault = IRODS_SHARED_REG_RESC_VAULT
    if os.path.exists(vault):
        return vault
    else:
        return None

def get_register_resource(session):
    vault_path = irods_shared_reg_resc_vault()
    Reg_Resc_Name = ''
    if vault_path:
        session.resources.create(IRODS_REG_RESC, 'unixfilesystem', session.host, vault_path)
        Reg_Resc_Name = IRODS_REG_RESC
    return Reg_Resc_Name


def make_environment_and_auth_files( dir_, **params ):
    if not os.path.exists(dir_): os.mkdir(dir_)
    def recast(k):
        return 'irods_' + k + ('_name' if k in ('user','zone') else '')
    config = os.path.join(dir_,'irods_environment.json')
    with open(config,'w') as f1:
        json.dump({recast(k):v for k,v in params.items() if k != 'password'},f1,indent=4)
    auth = os.path.join(dir_,'.irodsA')
    with open(auth,'w') as f2:
        f2.write(encode(params['password']))
    os.chmod(auth,0o600)
    return (config, auth)


def make_session(**kwargs):
    try:
        env_file = kwargs.pop('irods_env_file')
    except KeyError:
        try:
            env_file = os.environ['IRODS_ENVIRONMENT_FILE']
        except KeyError:
            env_file = os.path.expanduser('~/.irods/irods_environment.json')

    try:
        os.environ['IRODS_CI_TEST_RUN']
        uid = getpwnam('irods').pw_uid
    except KeyError:
        uid = None

    return iRODSSession( irods_authentication_uid = uid, irods_env_file = env_file, **kwargs )


def home_collection(session):
    return "/{0.zone}/home/{0.username}".format(session)


def make_object(session, path, content=None, **options):
    if content is None:
        content = u'blah'

    content = iRODSMessage.encode_unicode(content)

    if session.server_version <= (4,1,4):
        # 2 step open-create necessary for iRODS 4.1.4 or older
        obj = session.data_objects.create(path)
        with obj.open('w', **options) as obj_desc:
            obj_desc.write(content)
    else:
        with session.data_objects.open(path, 'w', **options) as obj_desc:
            obj_desc.write(content)

    # refresh object after write
    return session.data_objects.get(path)


def make_collection(session, path, object_names=None, object_content=None):
    # create collection
    coll = session.collections.create(path)

    # create objects
    if object_names:
        for name in object_names:
            obj_path = os.path.join(path, name)
            make_object(session, obj_path, content=object_content)

    return coll


def make_test_collection(session, path, obj_count):
    coll = session.collections.create(path)

    for n in range(obj_count):
        obj_path = path + "/test" + str(n).zfill(6) + ".txt"
        make_object(session, obj_path)

    return coll


def make_deep_collection(session, root_path, depth=10, objects_per_level=50, object_content=None):
    # start at root path
    current_coll_path = root_path

    # make collections recursively
    for d in range(depth):
        # make list of object names
        obj_names = ['obj' + str(i).zfill(len(str(objects_per_level)))
                     for i in range(objects_per_level)]

        # make subcollection and objects
        if d == 0:
            root_coll = make_collection(
                session, current_coll_path, obj_names, object_content)
        else:
            make_collection(
                session, current_coll_path, obj_names, object_content)

        # next level down
        current_coll_path = os.path.join(
            current_coll_path, 'subcoll' + str(d).zfill(len(str(d))))

    return root_coll


def make_flat_test_dir(dir_path, file_count=10, file_size=1024):
    if file_count < 1:
        raise ValueError

    os.mkdir(dir_path)

    for i in range(file_count):
        # pad file name suffix with zeroes
        suffix_width = int(math.log10(file_count))+1
        file_path = '{dir_path}/test_{i:0>{suffix_width}}.txt'.format(**locals())

        # make random binary file
        with open(file_path, 'wb') as f:
            f.write(os.urandom(file_size))

@contextlib.contextmanager
def create_simple_resc (self, rescName = None):
    if not rescName: 
        rescName =  'simple_resc_' + unique_name (my_function_name() + '_simple_resc', datetime.datetime.now())
    created = False
    try:
        self.sess.resources.create(rescName,
                                   'unixfilesystem',
                                   host = self.sess.host,
                                   path = '/tmp/' + rescName)
        created = True
        yield rescName
    finally:
        if created:
            self.sess.resources.remove(rescName)

@contextlib.contextmanager
def create_simple_resc_hierarchy (self, Root, Leaf):
    d = tempfile.mkdtemp()
    self.sess.resources.create(Leaf,'unixfilesystem',
                           host = self.sess.host,
                           path=d)
    self.sess.resources.create(Root,'passthru')
    self.sess.resources.add_child(Root,Leaf)
    try:
        yield ';'.join([Root,Leaf])
    finally:
        self.sess.resources.remove_child(Root,Leaf)
        self.sess.resources.remove(Leaf)
        self.sess.resources.remove(Root)
        shutil.rmtree(d)


def chunks(f, chunksize=io.DEFAULT_BUFFER_SIZE):
    return iter(lambda: f.read(chunksize), b'')


def compute_sha256_digest(file_path):
    hasher = hashlib.sha256()

    with open(file_path, 'rb') as f:
        for chunk in chunks(f):
            hasher.update(chunk)

    return base64.b64encode(hasher.digest()).decode()


def remove_unused_metadata(session):
    from irods.message import GeneralAdminRequest
    from irods.api_number import api_number
    message_body = GeneralAdminRequest( 'rm', 'unusedAVUs', '','','','')
    req = iRODSMessage("RODS_API_REQ", msg = message_body,int_info=api_number['GENERAL_ADMIN_AN'])
    with session.pool.get_connection() as conn:
        conn.send(req)
        response=conn.recv()
        if (response.int_info != 0): raise RuntimeError("Error removing unused AVUs")


@contextlib.contextmanager
def file_backed_up(filename):
    with tempfile.NamedTemporaryFile(prefix=os.path.basename(filename)) as f:
        shutil.copyfile(filename, f.name)
        try:
            yield filename
        finally:
            shutil.copyfile(f.name, filename)


def irods_session_host_local (sess):
    return socket.gethostbyname(sess.host) == \
           socket.gethostbyname(socket.gethostname())
