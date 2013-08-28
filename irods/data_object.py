from os import O_RDONLY, O_WRONLY, O_RDWR

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
        conn, desc = self.manager.open(self.path, flag)
        return iRODSDataObjectFile(conn, desc)

class iRODSDataObjectFile(object):
    def __init__(self, conn, descriptor):
        self.conn = conn
        self.desc = descriptor
        self.position = 0

    def tell(self):
        return self.position

    def close(self):
        try:
            self.conn.close_file(self.desc)
        except CAT_NO_ACCESS_PERMISSION:
            pass 
        finally:
            self.conn.release()
        return None

    def read(self, size=None):
        if not size:
            return "".join(self.read_gen()())
        contents = self.conn.read_file(self.desc, size)
        if contents:
            self.position += len(contents)
        return contents

    def read_gen(self, chunk_size=4096, close=False):
        def make_gen():
            while True:
                contents = self.read(chunk_size) 
                if not contents:
                    break
                yield contents
            if close:
                self.close()
        return make_gen

    def write(self, string):
        written = self.conn.write_file(self.desc, string)
        self.position += written
        return None

    def seek(self, offset, whence=0):
        pos = self.conn.seek_file(self.desc, offset, whence)
        self.position = pos
        pass

    def __iter__(self):
        reader = self.read_gen()
        chars = []
        for chunk in reader():
            for char in chunk:
                if char == '\n':
                    yield "".join(chars)
                    chars = []
                else:
                    chars.append(char)

    def readline(self):
        pass

    def readlines(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
