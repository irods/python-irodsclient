from os.path import basename
from models import Collection, DataObject
from data_object import iRODSDataObject
from meta import iRODSMetaCollection

class iRODSCollection(object):
    def __init__(self, sess, result=None):
        self.sess = sess
        if result:
            self.id = result[Collection.id]
            self.path = result[Collection.name]
            self.name = basename(result[Collection.name])
        self._meta = None

    @property
    def metadata(self):
        if not self._meta:
            self._meta = iRODSMetaCollection(self.sess, Collection, self.name)
        return self._meta

    @property
    def subcollections(self):
        query = self.sess.query(Collection)\
            .filter(Collection.parent_name == self.path)
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
