from irods import derived_auth_filename


class iRODSAccount:

    @property
    def derived_auth_file(self):
        return derived_auth_filename(self.env_file)

    def __init__(
        self,
        irods_host,
        irods_port,
        irods_user_name,
        irods_zone_name,
        irods_authentication_scheme="native",
        password=None,
        client_user=None,
        server_dn=None,
        client_zone=None,
        env_file="",
        **kwargs
    ):

        # Allowed overrides when cloning sessions. (Currently hostname only.)
        for k, v in kwargs.pop("_overrides", {}).items():
            if k == "irods_host":
                irods_host = v

        self.env_file = env_file

        # The '_auth_file' attribute will be written in the call to iRODSSession.configure,
        # if an .irodsA file from the client environment is used to load password information.
        self._auth_file = ""

        tuplify = lambda _: _ if isinstance(_, (list, tuple)) else (_,)
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
                if key.startswith("irods_"):
                    setattr(self, key[6:], value)
                else:
                    setattr(self, key, value)
            except TypeError:
                setattr(self, key, value)

        if client_user:
            self.client_user = client_user
            if client_zone:
                self.client_zone = client_zone
