from __future__ import absolute_import
import os
import io
import tempfile
import contextlib
import shutil
import hashlib
import base64
import math
from pwd import getpwnam
from irods.session import iRODSSession
from irods.message import iRODSMessage
from six.moves import range


def make_session(**kwargs):
    try:
        env_file = kwargs['irods_env_file']
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

    return iRODSSession(irods_authentication_uid=uid, irods_env_file=env_file)


def make_object(session, path, content=None, **options):
    if content is None:
        content = u'blah'

    content = iRODSMessage.encode_unicode(content)

    # 2 step open-create necessary for iRODS 4.1.4 or older
    obj = session.data_objects.create(path)
    with obj.open('w', **options) as obj_desc:
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
