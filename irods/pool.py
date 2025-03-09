import contextlib
import datetime
import logging
import threading
import os
import weakref

from irods import DEFAULT_CONNECTION_TIMEOUT
from irods.connection import Connection
from irods.ticket import Ticket

logger = logging.getLogger(__name__)


def attribute_from_return_value(attrname):
    def deco(method):
        def method_(self, *s, **kw):
            ret = method(self, *s, **kw)
            setattr(self, attrname, ret)
            return ret

        return method_

    return deco


DEFAULT_APPLICATION_NAME = "python-irodsclient"


def _adjust_timeout_to_pool_default(conn):
    set_timeout = conn.socket.gettimeout()
    desired_value = conn.pool.connection_timeout
    if desired_value == set_timeout:
        return
    conn.socket.settimeout(desired_value)


class Pool:

    def __init__(
        self, account, application_name="", connection_refresh_time=-1, session=None
    ):
        """
        Pool( account , application_name='' )
        Create an iRODS connection pool; 'account' is an irods.account.iRODSAccount instance and
        'application_name' specifies the application name as it should appear in an 'ips' listing.
        """

        self.set_session_ref(session)
        self._thread_local = threading.local()
        self.account = account
        self._lock = threading.RLock()
        self.active = set()
        self.idle = set()
        self.connection_timeout = DEFAULT_CONNECTION_TIMEOUT
        self.application_name = (
            os.environ.get("spOption", "")
            or application_name
            or DEFAULT_APPLICATION_NAME
        )
        self._need_auth = True

        if connection_refresh_time > 0:
            self.refresh_connection = True
            self.connection_refresh_time = connection_refresh_time
        else:
            self.refresh_connection = False
            self.connection_refresh_time = None

    @contextlib.contextmanager
    def no_auto_authenticate(self):
        import irods.helpers

        with irods.helpers.temporarily_assign_attribute(self, "_need_auth", False):
            yield self

    def set_session_ref(self, session):
        self.session_ref = weakref.ref(session) if session is not None else lambda: None

    @property
    def _conn(self):
        return getattr(self._thread_local, "_conn", None)

    @_conn.setter
    def _conn(self, conn_):
        setattr(self._thread_local, "_conn", conn_)

    @attribute_from_return_value("_conn")
    def get_connection(self):
        new_conn = False
        with self._lock:
            try:
                conn = self.idle.pop()

                curr_time = datetime.datetime.now()
                # If 'refresh_connection' flag is True and the connection was
                # created more than 'connection_refresh_time' seconds ago,
                # release the connection (as its stale) and create a new one
                if (
                    self.refresh_connection
                    and (curr_time - conn.create_time).total_seconds()
                    > self.connection_refresh_time
                ):
                    logger.debug(
                        f"Connection with id {id(conn)} was created more than {self.connection_refresh_time} seconds ago. "
                        "Releasing the connection and creating a new one."
                    )
                    # Since calling disconnect() repeatedly is safe, we call disconnect()
                    # here explicitly, instead of relying on the garbage collector to clean
                    # up the object and call disconnect(). This makes the behavior of the
                    # code more predictable as we are not relying on when garbage collector is called
                    conn.disconnect()
                    conn = Connection(self, self.account)
                    new_conn = True
                    logger.debug(f"Created new connection with id: {id(conn)}")
            except KeyError:
                conn = Connection(self, self.account)
                new_conn = True
                logger.debug(
                    f"No connection found in idle set. Created a new connection with id: {id(conn)}"
                )

            self.active.add(conn)

            sess = self.session_ref()
            if sess and sess.ticket__ and not sess.ticket_applied.get(conn, False):
                Ticket._lowlevel_api_request(conn, "session", sess.ticket__)
                sess.ticket_applied[conn] = True

            logger.debug(f"Adding connection with id {id(conn)} to active set")

            # If the connection we're about to make active was cached, it already has a socket object internal to it,
            # so we potentially have to modify it to have the desired timeout.
            if not new_conn:
                _adjust_timeout_to_pool_default(conn)

        logger.debug(f"num active: {len(self.active)}")
        logger.debug(f"num idle: {len(self.idle)}")

        return conn

    def release_connection(self, conn, destroy=False):
        with self._lock:
            if conn in self.active:
                self.active.remove(conn)
                logger.debug(f"Removed connection with id: {id(conn)} from active set")
                if not destroy:
                    # If 'refresh_connection' flag is True, update connection's 'last_used_time'
                    if self.refresh_connection:
                        conn.last_used_time = datetime.datetime.now()
                    self.idle.add(conn)
                    logger.debug(f"Added connection with id: {id(conn)} to idle set")
            elif conn in self.idle and destroy:
                logger.debug(f"Destroying connection with id: {id(conn)}")
                self.idle.remove(conn)
        logger.debug(f"num active: {len(self.active)}")
        logger.debug(f"num idle: {len(self.idle)}")
