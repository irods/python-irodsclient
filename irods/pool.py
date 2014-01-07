import logging

from irods.connection import Connection

logger = logging.getLogger(__name__)

class Pool(object):
    def __init__(self, account):
        self.account = account

        self.active = set()
        self.idle = set()
        
    def get_connection(self):
        try:
            conn = self.idle.pop()
        except KeyError:
            conn = Connection(self, self.account)
        self.active.add(conn)
        logger.debug('num active: %d' % len(self.active))
        return conn

    def release_connection(self, conn):
        self.active.remove(conn)
        self.idle.add(conn)
        logger.debug('num idle: %d' % len(self.idle))
