import logging
from connection import Connection

class Pool(object):
    def __init__(self, account):
        self.account = account
        self.active = set()
        self.num_released = 0
        
    def get_connection(self):
        conn = Connection(self, self.account)
        self.active.add(conn)
        logging.debug(len(self.active))
        return conn

    def release_connection(self, conn):
        self.num_released += 1
        logging.debug('release %d' % self.num_released)
