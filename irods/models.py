import logging
from column import Column, Integer, String, DateTime

class ModelBase(type):
    def __new__(cls, name, bases, attr):
        #logging.debug(name)
        #logging.debug(attr.iteritems())
        columns = [(x,y) for (x,y) in attr.iteritems() if isinstance(y, Column)]
        #logging.debug(columns)
        attr['_columns'] = columns
        #attr['_icat_column_names'] = [y.icat_key for (x,y) in columns]
        #logging.debug(attr['_icat_column_names'])
        return type.__new__(cls, name, bases, attr)

class Base(object):
    __metaclass__ = ModelBase

class User(Base):
    id = Column(Integer, 'USER_ID', 201)
    name = Column(String, 'USER_NAME', 202)
    type = Column(String, 'USER_TYPE', 203)
    zone = Column(String, 'USER_ZONE', 204)
    dn = Column(String, 'USER_DN', 205)
    info = Column(String, 'USER_INFO', 206)
    comment = Column(String, 'USER_COMMENT', 207)
    create_time = Column(DateTime, 'USER_CREATE_TIME', 208)
    modify_time = Column(DateTime, 'USER_MODIFY_TIME', 209)

class Collection(Base):
    id = Column(Integer, 'COLL_ID', 500)
    name = Column(String, 'COLL_NAME', 501)
    parent_name = Column(String, 'COLL_PARENT_NAME', 502)
    owner_name = Column(String, 'COLL_OWNER_NAME', 503)
    owner_zone = Column(String, 'COLL_OWNER_ZONE', 504)
    map_id = Column(String, 'COLL_MAP_ID', 505)
    inheritance = Column(String, 'COLL_INHERITANCE', 506)
    comments = Column(String, 'COLL_COMMENTS', 507)
    create_time = Column(DateTime, 'COLL_CREATE_TIME', 508)
    modify_time = Column(DateTime, 'COLL_MODIFY_TIME', 509)
