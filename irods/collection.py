from os.path import basename
from models import Collection, DataObject
from data_object import iRODSDataObject
from meta import iRODSMetaCollection
from resource_manager import ResourceManager
from message import iRODSMessage, CollectionRequest
from exception import CollectionNodesNotExist
from api_number import api_number

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
            self._meta = iRODSMetaCollection(self.sess, Collection, self.path)
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

class CollectionManager(ResourceManager):
    def get_collection(self, path):
        query = self.query(Collection).filter(Collection.name == path)
        results = self.execute_query(query)
        # todo implement this with .one() on query
        if results.length == 1:
            return iRODSCollection(self, results[0])
        else:
            raise CollectionDoesNotExist()

    def create_collection(self, path):
        message_body = CollectionRequest(
            collName=path,
            KeyValPair_PI=StringStringMap()
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body, 
            int_info=api_number['COLL_CREATE_AN'])
        with self.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
        return self.get_collection(path)

    def delete_collection(self, path):
        pass

    def move_collection(self, path):
        pass
