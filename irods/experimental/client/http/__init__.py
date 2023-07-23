import collections
import enum
import functools
import itertools
import json
import logging
import requests
import sys
from .iterator_functions import *

logger = logging.getLogger(__name__)
MAX_INT32 = 2**31-1
DEFAULT_PAGE_SIZE = 512

# -----

# Abstractions that let us either page through a general query <count> items at a time,
#  or treat it like a Pythonic generator aka stateful iterator.
#  (See the README.md in this directory.)

# TODO: The README is temporary. Make some better docs.

class _pageable: 
    def __init__(self, callable_):
        """callable_ is a function-like object called without parameters.
           It pages once through the set of query results and should be
           stateful in terms of maintaining current offset within the query.
        """
        self.callable_ = callable_
    def next_page(self):
        page = list(self.callable_())
        return page

class _iterable(_pageable):
    """Adapts a pageable interface to return one query row at a time.  An
       empty [] returned from next_page signals the end of query results.
    """
    @functools.wraps(_pageable.__init__)
    def __init__(self,*_):
        super().__init__(*_)
        self.__P = None
        self.index = 0
    # Allow iter() on instances.
    def __iter__(self): return self
    def __next__(self):
        """Called implicitly by any iteration over the _iterable instance.
           Returns one query row.
        """
        if self.__P is None or self.index >= len(self.__P):
            self.__P = self.next_page()
            self.index = 0
        if 0 == len(self.__P):
            raise StopIteration
        element = self.__P[self.index]
        self.index += 1
        return element

# -----

class HTTP_operation_error(RuntimeError):
    pass

def _normalized_columns(columns):
    if not isinstance(columns,(list,tuple)):
        columns = filter(None, (_.strip() for _ in columns.split(',')))

    # de-duplicate
    columns = collections.OrderedDict((col,None) for col in columns)

    col_names = tuple(columns.keys())
    cls = collections.namedtuple('row', col_names)
    return cls, ",".join(col_names)

class DataObject:
    class column:
        class enum(enum.Enum):
            DATA_ID = 401
            DATA_COLL_ID = 402
            DATA_NAME = 403
            DATA_REPL_NUM = 404
            # TODO: complete this list
        names = [k for k in enum.__members__.keys()]

class Collection:
    class column:
        class enum(enum.Enum):
            COLL_ID = 500
            COLL_NAME = 501
            # TODO: complete this list
        names = [k for k in enum.__members__.keys()]

    # for heavyweight style of getter only!
    def __init__(self, mgr, id_):
        self.id = id_
        self.mgr = mgr

    @property
    def name(self):
        return self.mgr.value_by_column_name( self.id, 'COLL_NAME' )

# -----------------
# Manager/heavyweight approach to a catalog object "getter":
#
# This is an approximation of the old PRC approach
#                   for getting an instance of a collection by its nain
#                   identifying data, the logical pathname.
#
# We most likely will not be doing things this way.
# (See Session.data_object_replicas() method below.)

class Manager:
    def __init__(self, session):
        sess = self.sess = session

    def value_by_column_name(self, id_, column_name:str):
        first_row = one(self.sess.genquery1(columns = [column_name],
                                            condition = "COLL_ID = '{}'", args = [id_]))
        return getattr(first_row, column_name)

class CollManager(Manager):

    def name_from_id(self, id_):
        return one(self.sess.genquery1(columns = ['COLL_NAME'],
                                   condition = "COLL_ID = '{}'", args = [id_])).COLL_NAME

    def get(self, collname):
        r = self.sess.genquery1( columns = 'COLL_ID',
                                 condition = "COLL_NAME = '{}'", args = [collname] )
        return Collection(self, int(one(r).COLL_ID))

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

    # -----------------
    # Thin/lightweight approach to catalog object "getter":
    #
    def data_object(self, logical_path, *, 
                    query_options=(('offset',0),('count',DEFAULT_PAGE_SIZE))):
        coll,data = logical_path.rsplit('/',1)
        # TODO: embedded quotes in object names will not work here.
        return self.genquery1(DataObject.column.names + Collection.column.names,
                "COLL_NAME = '{}' and DATA_NAME = '{}'".format(coll,data),
                extra_query_options=dict(query_options))

    # Each endpoint can have its own method definition.

    def genquery1(self, columns, condition='', *, args=(), extra_query_options = ()):
        """Return a generator-style iterator over all row results.
           Example:
               for row in session.genquery1( 'COLL_NAME' ):
                   print(row.COLL_NAME)

           By default, one HTTP call to the server returns a single "row", which is not`
           terribly efficient.  We can override the "count" option with an arbitrary
           positive integer:

               session.genquery1(columns, extra_query_options=dict(count=512)).

           and since this function is agnostic to pagesize and simply returns a row-wise
           iterator, its row-wise iterative behavior will not change.
        """
        condition = condition.format(*args)
        row_class, columns = _normalized_columns(columns)
        where = '' if condition == '' else ' WHERE '

        # d's default argument (being mutable) gets memoized in the context of the
        # current closure, which persists beyond in the genquery1 call frame in which it
        # originated and persists and across multiple calls to get_r.
        # This can be leveraged to increment the query offset at the end of each get_r call
        # by the length of the rows array retrieved.

        def get_r(local_ = locals(), d = dict(extra_query_options)):
            if 'offset' not in d:
                d['offset'] = 0
            d['offset'] = int(d['offset'])
            result = self.http_get('/query',
                                   op = "execute_genquery",
                                   query = "SELECT {columns}{where}{condition}".format(**local_),
                                   **d)
            json_result = json.loads(result)
            errcode = json_result['irods_response']['error_code']
            if errcode != 0:
                logger.warn('irods error code of [%s] in genquery1',errcode)
            rows = [row_class(*i) for i in json_result['rows']]
            d['offset'] += len(rows)
            return rows

        return _iterable(get_r)

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
