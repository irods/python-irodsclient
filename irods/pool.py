from __future__ import absolute_import
import datetime
import logging
import threading
import os

from irods import DEFAULT_CONNECTION_TIMEOUT
from irods.connection import Connection

logger = logging.getLogger(__name__)


DEFAULT_APPLICATION_NAME = 'python-irodsclient'


class Pool(object):

    def __init__(self, account, application_name='', connection_refresh_time=-1):
        '''
        Pool( account , application_name='' )
        Create an iRODS connection pool; 'account' is an irods.account.iRODSAccount instance and
        'application_name' specifies the application name as it should appear in an 'ips' listing.
        '''
        self.account = account
        self._lock = threading.RLock()
        self.active = set()
        self.idle = set()
        self.connection_timeout = DEFAULT_CONNECTION_TIMEOUT
        self.application_name = ( os.environ.get('spOption','') or
                                  application_name or
                                  DEFAULT_APPLICATION_NAME )

        if connection_refresh_time > 0:
            self.refresh_connection = True
            self.connection_refresh_time = connection_refresh_time
        else:
            self.refresh_connection = False
            self.connection_refresh_time = None

    def get_connection(self):
        with self._lock:
            try:
                conn = self.idle.pop()

                curr_time = datetime.datetime.now()
                # If 'refresh_connection' flag is True and the connection was
                # last used more than 'connection_refresh_time' seconds ago,
                # release the connection (as its stale) and create a new one
                if self.refresh_connection and (curr_time - conn.last_used_time).total_seconds() > self.connection_refresh_time:
                    logger.debug('Connection has been idle more than {} seconds. Releasing the connection and creating a new one.'.format(self.connection_refresh_time))
                    self.release_connection(conn, True)
                    conn = Connection(self, self.account)
            except KeyError:
                conn = Connection(self, self.account)

            self.active.add(conn)
        logger.debug('num active: {}'.format(len(self.active)))
        return conn

    def release_connection(self, conn, destroy=False):
        with self._lock:
            if conn in self.active:
                self.active.remove(conn)
                if not destroy:
                    # If 'refresh_connection' flag is True, update connection's 'last_used_time'
                    if self.refresh_connection:
                        conn.last_used_time = datetime.datetime.now()
                    self.idle.add(conn)
            elif conn in self.idle and destroy:
                self.idle.remove(conn)
        logger.debug('num idle: {}'.format(len(self.idle)))
