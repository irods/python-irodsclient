from os import O_RDONLY, O_WRONLY, O_RDWR
from io import RawIOBase, BufferedRandom

from irods.models import DataObject
from irods.meta import iRODSMetaCollection
from irods.exception import CAT_NO_ACCESS_PERMISSION

class iRODSDataObject(object):
    def __init__(self, manager, parent=None, result=None):
        self.manager = manager
        if parent and result:
            self.collection = parent
            for attr in ['id', 'name', 'size', 'checksum', 'create_time', 
                'modify_time']:
                setattr(self, attr, result[getattr(DataObject, attr)])
            self.path = self.collection.path + '/' + self.name
        self._meta = None

    def __repr__(self):
        return "<iRODSDataObject %d %s>" % (self.id, self.name)

    @property
    def metadata(self):
        if not self._meta:
            self._meta = iRODSMetaCollection(self.manager.sess.metadata, DataObject, self.path)
        return self._meta

    def open(self, mode='r'):
        flag, create_if_not_exists, seek_to_end = {
            'r': (O_RDONLY, False, False),
            'r+': (O_RDWR, False, False),
            'w': (O_WRONLY, True, False),
            'w+': (O_RDWR, True, False),
            'a': (O_WRONLY, True, True),
            'a+': (O_RDWR, True, True),
        }[mode]
        # TODO: Actually use create_if_not_exists and seek_to_end
        conn, desc = self.manager.open(self.path, flag)
        return BufferedRandom(iRODSDataObjectFileRaw(conn, desc))

    def unlink(self):
        self.manager.unlink(self.path)

class iRODSDataObjectFileRaw(RawIOBase):
    def __init__(self, conn, descriptor):
        self.conn = conn
        self.desc = descriptor

    def close(self):
        try:
            self.conn.close_file(self.desc)
        except CAT_NO_ACCESS_PERMISSION:
            pass 
        finally:
            self.conn.release()
        return None

    def seek(self, offset, whence=0):
        return self.conn.seek_file(self.desc, offset, whence)

    def readinto(self, b):
        contents = self.conn.read_file(self.desc, len(b))
        if contents is None:
            return 0
        for i, c in enumerate(contents):
            b[i] = c
        return len(contents)

    def write(self, b):
        return self.conn.write_file(self.desc, str(b.tobytes()))

    def readable(self):
        return True

    def writable(self):
        return True

    def seekable(self):
        return True
