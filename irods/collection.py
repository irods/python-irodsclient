from os.path import basename

from models import Collection, DataObject
from data_object import iRODSDataObject
from meta import iRODSMetaCollection
from resource_manager import ResourceManager
from message import iRODSMessage, CollectionRequest, StringStringMap
from exception import CollectionDoesNotExist
from api_number import api_number

class iRODSCollection(object):
    def __init__(self, manager, result=None):
        self.manager = manager
        if result:
            self.id = result[Collection.id]
            self.path = result[Collection.name]
            self.name = basename(result[Collection.name])
        self._meta = None

    @property
    def metadata(self):
        if not self._meta:
            self._meta = iRODSMetaCollection(self.manager.sess.metadata, 
                Collection, self.path)
        return self._meta

    @property
    def subcollections(self):
        query = self.manager.sess.query(Collection)\
            .filter(Collection.parent_name == self.path)
        results = self.manager.sess.execute_query(query)
        return [iRODSCollection(self.manager, row) for row in results]

    @property
    def data_objects(self):
        query = self.manager.sess.query(DataObject)\
            .filter(DataObject.collection_id == self.id)
        results = self.manager.sess.execute_query(query)
        return [
            iRODSDataObject(self.manager.sess.data_objects, self, row) 
            for row in results
        ]

    def __repr__(self):
        return "<iRODSCollection %d %s>" % (self.id, self.name)

class CollectionManager(ResourceManager):
    def get(self, path):
        query = self.sess.query(Collection).filter(Collection.name == path)
        results = self.sess.execute_query(query)
        # todo implement this with .one() on query
        if results.length == 1:
            return iRODSCollection(self, results[0])
        else:
            raise CollectionDoesNotExist()

    def create(self, path):
        message_body = CollectionRequest(
            collName=path,
            KeyValPair_PI=StringStringMap()
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body, 
            int_info=api_number['COLL_CREATE_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
        return self.get_collection(path)

    def delete(self, path):
        pass

    def move(self, path):
        pass
