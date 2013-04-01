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
        return self.sess.get_file(self.full_path, mode)
