from irods.test.helpers import make_session, home_collection
import ssl

# Exercise an API to instantiate a connection.
session = make_session()
home = home_collection(session)
session.collections.get(home)

# Assert that the resulting connection is SSL-enabled.
connections = session.pool.active | session.pool.idle
is_SSL = len(connections) > 0 and all(
    isinstance(conn.socket, ssl.SSLSocket) for conn in connections
)
exit(0 if is_SSL else 1)
