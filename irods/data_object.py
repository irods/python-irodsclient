from os import O_RDONLY, O_WRONLY, O_RDWR
from models import DataObject
from meta import iRODSMetaCollection
SEEK_SET = 0
SEEK_CUR = 1
SEEK_END = 2

class iRODSDataObject(object):
    def __init__(self, sess, parent=None, result=None):
        self.sess = sess
        if parent:
            self.collection = parent
        if result:
            self.id = result[DataObject.id]
            self.name = result[DataObject.name]
            self.full_path = self.collection.name + '/' + self.name

    def __repr__(self):
        return "<iRODSDataObject %d %s>" % (self.id, self.name)

    @property
    def metadata(self):
        if not self._meta:
            self._meta = iRODSMetaCollection(DataObject, self.full_path)
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
        desc = self.sess.open_file(self.full_path, flag)
        return iRODSDataObjectFile(self.sess, desc)

class iRODSDataObjectFile(object):
    def __init__(self, session, descriptor):
        self.sess = session
        self.desc = descriptor
        self.position = 0

    def tell(self):
        return self.position

    def close(self):
        self.sess.close_file(self.desc)
        return None

    def read(self, size=None):
        if not size:
            return "".join(self._read_all())
        contents = self.sess.read_file(self.desc, size)
        if contents:
            self.position += len(contents)
        return contents

    def _read_all(self):
        while True:
            contents = self.read(4096) 
            if not contents:
                break
            yield contents

    def write(self, string):
        written = self.sess.write_file(self.desc, string)
        self.position += written
        return None

    def seek(self, offset, whence=0):
        pos = self.sess.seek_file(self.desc, offset, whence)
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
