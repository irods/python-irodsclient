import logging

from irods.connection import Connection

class Pool(object):
    def __init__(self, account, proxy_user=None, proxy_zone=None):
        self.account = account
        self.proxy_user = proxy_user

        if proxy_user:
            self.proxy_zone = proxy_zone if proxy_zone else account.zone
        else:
            self.proxy_zone = None

        self.active = set()
        self.idle = set()
        
    def get_connection(self):
        try:
            conn = self.idle.pop()
        except KeyError:
            conn = Connection(self, self.account, self.proxy_user, self.proxy_zone)
        self.active.add(conn)
        logging.debug('num active: %d' % len(self.active))
        return conn

    def release_connection(self, conn):
        self.active.remove(conn)
        self.idle.add(conn)
        logging.debug('num idle: %d' % len(self.idle))
