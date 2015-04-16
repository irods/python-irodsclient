import os
import sys


def make_dummy_object(session, path):
    content = 'blah'

    obj = session.data_objects.create(path)
    with obj.open('w') as obj_desc:
        obj_desc.write(content)

    return obj


def make_dummy_collection(session, path, obj_count):
    coll = session.collections.create(path)

    for n in range(obj_count):
        obj_path = path + "/dummy" + str(n).zfill(6) + ".txt"
        make_dummy_object(session, obj_path)

    return coll
