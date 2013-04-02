from models import DataObject

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

    def open(self, mode):
        desc = self.sess.get_file(self.full_path, mode)
        return iRODSDataObjectFile(self.sess, desc)

class iRODSDataObjectFile(object):
    def __init__(self, session, descriptor):
        self.sess = session
        self.desc = descriptor

    def close(self):
        pass

    def read(self, length):
        pass

    def write(self, string, length=None):
        pass

    def seek(self, offset, whence):
        pass

    def rewind(self):
        pass
