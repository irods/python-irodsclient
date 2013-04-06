from connection import Connection

class Pool(object):
    def __init__(self, account):
        self.account = account
        
    def get_connection(self):
        return Connection(self, self.account)

    def release_connection(self, conn):
        pass
