from models import DataObject

class iRODSDataObject(object):
    def __init__(self, sess, result=None):
        self.sess = sess
        if result:
            self.id = result[DataObject.id]
            self.name = result[DataObject.name]

    def __repr__(self):
        return "<iRODSDataObject %d %s>" % (self.id, self.name)
