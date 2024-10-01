import requests
import collections

class HTTP_connect_failed(RuntimeError):
    pass

class Session:

    url_base_template = 'http://{self.host}:{self.port}/irods-http-api/{self.version}'

    @property
    def url_base(self):
        return self.url_base_template.format(**locals())

    def __init__(self, username, password, *,
                 host = 'localhost',
                 port = 9000,
                 version = '0.9.5'):

        self.username = username
        self.password = password
        (self.host, self.port, self.version) = (host, port, version)

        r = requests.post(self.url_base + '/authenticate', auth=(self.username, self.password))
        if r.status_code != 200 or not r.text:
            raise HTTP_connect_failed
        self.bearer_token = r.text



if __name__ == '__main__':
    Session('rods','rods',host='192.168.0.5')
