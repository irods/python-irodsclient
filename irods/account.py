import os

class iRODSAccount(object):

    @property
    def derived_auth_file(self):
        return '' if not self.env_file else os.path.join(os.path.dirname(self.env_file),'.irodsA')

    def __init__(self, irods_host, irods_port, irods_user_name, irods_zone_name,
                 irods_authentication_scheme='native',
                 password=None, client_user=None,
                 server_dn=None, client_zone=None,
                 env_file = '',
                 **kwargs):


        # Allowed overrides when cloning sessions. (Currently hostname only.)
        for k,v in kwargs.pop('_overrides',{}).items():
            if k =='irods_host':
                irods_host = v

        self.env_file = env_file
        tuplify = lambda _: _ if isinstance(_,(list,tuple)) else (_,)
        schemes = [_.lower() for _ in tuplify(irods_authentication_scheme)]

        self._original_authentication_scheme = schemes[-1]
        self.authentication_scheme = schemes[0]

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
