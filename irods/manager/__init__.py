class Manager(object):

    __server_version = ()

    @property
    def server_version(self):
        if not self.__server_version:
            p = self.sess.pool
            if p is None : raise RuntimeError ("session not configured")
            conn = getattr(p,"_conn",None) or p.get_connection()
            if conn: self.__server_version = conn.server_version
        return tuple( self.__server_version )

    def __init__(self, sess):
        self.sess = sess
