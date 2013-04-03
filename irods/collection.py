from models import Collection, DataObject
from data_object import iRODSDataObject

class iRODSCollection(object):
    def __init__(self, sess, result=None):
        self.sess = sess
        if result:
            self.id = result[Collection.id]
            self.name = result[Collection.name]

    @property
    def subcollections(self):
        query = self.sess.query(Collection)\
            .filter(Collection.parent_name == self.name)
        results = self.sess.execute_query(query)
        return [iRODSCollection(self.sess, row) for row in results]

    @property
    def data_objects(self):
        query = self.sess.query(DataObject)\
            .filter(DataObject.collection_id == self.id)
        results = self.sess.execute_query(query)
        return [iRODSDataObject(self.sess, self, row) for row in results]

    def __repr__(self):
        return "<iRODSCollection %d %s>" % (self.id, self.name)
