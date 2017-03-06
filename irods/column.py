from __future__ import absolute_import
from datetime import datetime
from calendar import timegm


class QueryKey(object):

    def __init__(self, column_type):
        self.column_type = column_type

    def __lt__(self, other):
        return Criterion('<', self, other)

    def __le__(self, other):
        return Criterion('<=', self, other)

    def __eq__(self, other):
        return Criterion('=', self, other)

    def __ne__(self, other):
        return Criterion('<>', self, other)

    def __gt__(self, other):
        return Criterion('>', self, other)

    def __ge__(self, other):
        return Criterion('>=', self, other)


class Criterion(object):

    def __init__(self, op, query_key, value):
        self.op = op
        self.query_key = query_key
        self.value = self.query_key.column_type.to_irods(value)


class Column(QueryKey):

    def __init__(self, column_type, icat_key, icat_id):
        self.icat_key = icat_key
        self.icat_id = icat_id
        super(Column, self).__init__(column_type)

    def __repr__(self):
        return "<%s.%s %d %s>" % (
            self.__class__.__module__,
            self.__class__.__name__,
            self.icat_id,
            self.icat_key
        )

    def __hash__(self):
        return hash((self.column_type, self.icat_key, self.icat_id))


class Keyword(QueryKey):

    def __init__(self, column_type, icat_key):
        self.icat_key = icat_key
        super(Keyword, self).__init__(column_type)

# consider renaming columnType


class ColumnType(object):

    @staticmethod
    def to_python(string):
        pass

    @staticmethod
    def to_irods(data):
        pass


class Integer(ColumnType):

    @staticmethod
    def to_python(string):
        return int(string)

    @staticmethod
    def to_irods(data):
        return "'%s'" % str(data)


class String(ColumnType):

    @staticmethod
    def to_python(string):
        return string

    @staticmethod
    def to_irods(data):
        return "'%s'" % data


class DateTime(ColumnType):

    @staticmethod
    def to_python(string):
        return datetime.utcfromtimestamp(int(string))

    @staticmethod
    def to_irods(data):
        return "'%011d'" % timegm(data.utctimetuple())
