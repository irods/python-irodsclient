from __future__ import absolute_import
import os
import io
import tempfile
import contextlib
import shutil
import irods.test.config as config
from irods.session import iRODSSession
from irods.message import iRODSMessage
from six.moves import range


def make_session_from_config(**kwargs):
    conf_map = {'host': 'IRODS_SERVER_HOST',
                'port': 'IRODS_SERVER_PORT',
                'zone': 'IRODS_SERVER_ZONE',
                'user': 'IRODS_USER_USERNAME',
                'authentication_scheme': 'IRODS_AUTHENTICATION_SCHEME',
                'password': 'IRODS_USER_PASSWORD',
                'server_dn': 'IRODS_SERVER_DN'}
    for key in conf_map.keys():
        try:
            kwargs[key] = vars(config)[conf_map[key]]
        except KeyError:
            pass

    return iRODSSession(**kwargs)


def make_object(session, path, content=None, options=None):
    if content is None:
        content = u'blah'

    content = iRODSMessage.encode_unicode(content)

    # 2 step open-create necessary for iRODS 4.1.4 or older
    obj = session.data_objects.create(path)
    with obj.open('w', options) as obj_desc:
        obj_desc.write(content)

    # refresh object after write
    return session.data_objects.get(path)

def chunks(f, chunksize=io.DEFAULT_BUFFER_SIZE):
    return iter(lambda: f.read(chunksize), b'')


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


@contextlib.contextmanager
def file_backed_up(filename):
    with tempfile.NamedTemporaryFile(prefix=os.path.basename(filename)) as f:
        shutil.copyfile(filename, f.name)
        try:
            yield filename
        finally:
            shutil.copyfile(f.name, filename)
