from os import O_RDONLY, O_WRONLY, O_RDWR
from models import DataObject
from meta import iRODSMetaCollection
SEEK_SET = 0
SEEK_CUR = 1
SEEK_END = 2

class iRODSDataObject(object):
    def __init__(self, sess, parent=None, result=None):
        self.sess = sess
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
            self._meta = iRODSMetaCollection(self.sess, DataObject, self.path)
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
        conn, desc = self.sess.open_file(self.path, flag)
        return iRODSDataObjectFile(conn, desc)

class iRODSDataObjectFile(object):
    def __init__(self, conn, descriptor):
        self.conn = conn
        self.desc = descriptor
        self.position = 0

    def tell(self):
        return self.position

    def close(self):
        self.conn.close_file(self.desc)
        return None

    def read(self, size=None):
        if not size:
            return "".join(self.read_gen())
        contents = self.conn.read_file(self.desc, size)
        if contents:
            self.position += len(contents)
        return contents

    def read_gen(self, chunk_size=4096):
        def make_gen():
            while True:
                contents = self.read(chunk_size) 
                if not contents:
                    break
                yield contents
        return make_gen

    def write(self, string):
        written = self.conn.write_file(self.desc, string)
        self.position += written
        return None

    def seek(self, offset, whence=0):
        pos = self.conn.seek_file(self.desc, offset, whence)
        self.position = pos
        pass

    def readline(self):
        pass

    def readlines(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
