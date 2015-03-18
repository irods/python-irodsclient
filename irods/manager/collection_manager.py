from irods.models import Collection
from irods.manager import Manager
from irods.message import iRODSMessage, CollectionRequest, StringStringMap
from irods.exception import CollectionDoesNotExist, NoResultFound
from irods.api_number import api_number
from irods.collection import iRODSCollection
from irods.constants import SYS_SVR_TO_CLI_COLL_STAT, SYS_CLI_TO_SVR_COLL_STAT_REPLY


class CollectionManager(Manager):
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
            int_info=api_number['COLL_CREATE_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
        return self.get(path)

    def remove(self, path, recurse=True, force=False, additional_flags={}):
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
            int_info=api_number['RM_COLL_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
            
            while response.int_info == SYS_SVR_TO_CLI_COLL_STAT:
                conn.reply(SYS_CLI_TO_SVR_COLL_STAT_REPLY)
                response = conn.recv()


