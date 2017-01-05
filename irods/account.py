class iRODSAccount(object):

    def __init__(self, host, port, user, zone,
                 authentication_scheme='password',
                 password=None, client_user=None,
                 server_dn=None, client_zone=None):

        self.authentication_scheme = authentication_scheme.lower()
        self.host = host
        self.port = port
        self.proxy_user = self.client_user = user
        self.proxy_zone = self.client_zone = zone
        self.server_dn = server_dn
        self.password = password

        if client_user:
            self.client_user = client_user
            if client_zone:
                self.client_zone = client_zone
