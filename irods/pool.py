import logging

from irods.connection import Connection

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
        logging.debug('num active: %d' % len(self.active))
        return conn

    def release_connection(self, conn):
        self.active.remove(conn)
        self.idle.add(conn)
        logging.debug('num idle: %d' % len(self.idle))
