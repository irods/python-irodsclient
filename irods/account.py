class iRODSAccount(object):

    def __init__(self, irods_host, irods_port, irods_user_name, irods_zone_name,
                 irods_authentication_scheme='native',
                 password=None, client_user=None,
                 server_dn=None, client_zone=None, **kwargs):

        self.authentication_scheme = irods_authentication_scheme.lower()
        self.host = irods_host
        self.port = int(irods_port)
        self.proxy_user = self.client_user = irods_user_name
        self.proxy_zone = self.client_zone = irods_zone_name
        self.server_dn = server_dn
        self.password = password

        for key, value in kwargs.items():
            try:
                if key.startswith('irods_'):
                    setattr(self, key[6:], value)
                else:
                    setattr(self, key, value)
            except TypeError:
                setattr(self, key, value)

        if client_user:
            self.client_user = client_user
            if client_zone:
                self.client_zone = client_zone
