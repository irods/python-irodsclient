class iRODSAccount(object):
    def __init__(self, host, port, user, zone, password):
        self.host = host
        self.port = port
        self.user = user
        self.zone = zone
        self.password = password
