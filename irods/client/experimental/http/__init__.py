import collections
import json
import logging
import requests
import sys

def _normalized_columns(columns):
    if not isinstance(columns,(list,tuple)):
        columns = filter(None, (_.strip() for _ in columns.split(',')))

    # de-duplicate
    columns = collections.OrderedDict((col,None) for col in columns)

    col_names = tuple(columns.keys())
    cls = collections.namedtuple('row', col_names)
    return cls, ",".join(col_names)

logger = logging.getLogger(__name__)

class HTTP_operation_error(RuntimeError):
    pass

class Collection:

    def __init__(self, mgr, id_):
        self.id = id_
        self.mgr = mgr

    @property
    def name(self):
        return self.mgr.value_by_column_name( self.id, 'COLL_NAME' )

# -----------------

class Manager:
    def __init__(self, session):
        sess = self.sess = session

    def value_by_column_name(self, id_, column_name:str):
        first_row = self.sess.genquery1(columns = [column_name],
                                        condition = "COLL_ID = '{}'", args = [id_])[0]
        return getattr(first_row, column_name)

class CollManager(Manager):

    def name_from_id(self, id_):
        return self.sess.genquery1(columns = ['COLL_NAME'],
                                   condition = "COLL_ID = '{}'", args = [id_])[0].COLL_NAME

    def get(self, collname):
        jr = self.sess.genquery1( columns = 'COLL_ID',
                                  condition = "COLL_NAME = '{}'", args = [collname] )
        return Collection(self, int(jr[0].COLL_ID))

# -----------------

class Session:

    url_base_template = 'http://{self.host}:{self.port}/irods-http/{self.version}'

    # Convenient object properties.

    @property
    def url_base(self):
        return self.url_base_template.format(**locals())

    def url(self, endpoint_name):
        return self.url_base + "/" + endpoint_name.strip("/")

    @property
    def auth_header(self):
        return {'Authorization': 'Bearer ' + self.bearer_token}

    # Low-level basis for implementing an endpoint via HTTP 'GET'.

    def http_get(self, endpoint_name, **param_key_value_pairs):
        r = requests.get( self.url(endpoint_name),
                          headers = self.auth_header,
                          params = param_key_value_pairs )
        if not r.ok:
            raise HTTP_operation_error("Failed in GET.")
        return r.content.decode()

    # Each endpoint can have its own method definition.

    def genquery1(self, columns, condition='', *, args=(), extra_query_options = ()):
        ## maybe require Python3.8 so we can have format strings, for example -
        # query_text = f"SELECT {columns} where {condition.format(*args)}"
        condition = condition.format(*args)
        cls, columns = _normalized_columns(columns)
        where = '' if condition == '' else ' WHERE '
        r = self.http_get( '/query',
                           op = "execute_genquery",
                           query = "SELECT {columns}{where}{condition}".format(**locals()),
                           **dict(extra_query_options))
        J = json.loads(r)
        errcode = J['irods_response']['error_code']
        if errcode != 0:
            logger.warn('irods error code of [%s] in genquery1',errcode)
        return [cls(*i) for i in J['rows']]

    def __init__(self, username, password, *,
                 host = 'localhost',
                 port = 9000,
                 version = '0.9.5'):

        self.username = username
        self.password = password
        (self.host, self.port, self.version) = (host, port, version)
        url = self.url_base + '/authenticate'
        r = requests.post(url, auth = (self.username, self.password))
        if not r.ok:
            raise HTTP_operation_error("Failed to connect: url = '%s', status code = %s",
                                       url, r.status_code)
        self.bearer_token = r.text

