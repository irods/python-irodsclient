import logging

def model_base(name, bases, attr):
    columns = [(x,y) for (x,y) in attr.iteritems() if y.__class__ == Column]
    attr['_icat_column_names'] = [y.icat_key for (x,y) in columns]
    return type(name, bases, attr)

class Column(object):
    def __init__(self, type, icat_key):
        self.type = type
        self.icat_key = icat_key

class ColumnType(object):
    def to_python(self):
        pass

class Integer(ColumnType):
    @staticmethod
    def to_python(str):
        return int(str) 

class String(ColumnType):
    @staticmethod
    def to_python(str):
        return str

class DateTime(ColumnType):
    @staticmethod
    def to_python(str):
        return str

class User(object):
    __metaclass__ = model_base
    id = Column(Integer, 'USER_ID')
    name = Column(String, 'USER_NAME')
    type = Column(String, 'USER_TYPE')
    zone = Column(String, 'USER_ZONE')
    create_time = Column(DateTime, 'USER_CREATE_TIME')
    modify_time = Column(DateTime, 'USER_MODIFY_TIME')

class Collection(object):
    __metaclass__ = model_base
    id = Column(Integer, 'COLL_ID')
    name = Column(String, 'COLL_NAME')
    parent_name = Column(String, 'COLL_PARENT_NAME')
    owner_name = Column(String, 'OWNER_NAME')
    owner_zone = Column(String, 'OWNER_ZONE')
    create_time = Column(DateTime, 'CREATE_TIME')
    modify_time = Column(DateTime, 'MODIFY_TIME')
