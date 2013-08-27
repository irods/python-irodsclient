from models import Collection
from resource_manager import ResourceManager
from message import iRODSMessage, CollectionRequest, StringStringMap
from exception import CollectionDoesNotExist, NoResultFound
from api_number import api_number

class CollectionManager(ResourceManager):
    def get(self, path):
        query = self.sess.query(Collection).filter(Collection.name == path)
        try:
            result = query.one()
        except NoResultFound:
            raise CollectionDoesNotExist()
        return iRODSCollection(self, result)
            
    def create(self, path):
        message_body = CollectionRequest(
            collName=path,
            KeyValPair_PI=StringStringMap()
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body, 
            int_info=api_number['COLL_CREATE201_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
        return self.get(path)

    def delete(self, path, recurse=True, force=False, additional_flags={}):
        options = {}
        if recurse:
            options['recursiveOpr'] = ''
        if force:
            options['forceFlag'] = ''
        options = dict(options.items() + additional_flags.items())
        message_body = CollectionRequest(
            collName=path,
            KeyValPair_PI=StringStringMap(options)
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
            int_info=api_number['RM_COLL_OLD201_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()

    def move(self, path):
        pass
