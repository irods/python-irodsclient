from __future__ import absolute_import
import six
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
        self._value = value

    @property
    def value(self):
        return self.query_key.column_type.to_irods(self._value)

class In(Criterion):

    def __init__(self, query_key, value):
        super(In, self).__init__('in', query_key, value)

    @property
    def value(self):
        v = "("
        comma = ""
        for element in self._value:
            v += "{}'{}'".format(comma,element)
            comma = ","
        v += ")"
        return v

class Like(Criterion):

    def __init__(self, query_key, value):
        super(Like, self).__init__('like', query_key, value)


class Between(Criterion):

    def __init__(self, query_key, value):
        super(Between, self).__init__('between', query_key, value)

    @property
    def value(self):
        lower_bound, upper_bound = self._value
        return "{} {}".format(self.query_key.column_type.to_irods(lower_bound),
                              self.query_key.column_type.to_irods(upper_bound))


class Column(QueryKey):

    def __init__(self, column_type, icat_key, icat_id, min_version=(0,0,0)):
        self.icat_key = icat_key
        self.icat_id = icat_id
        self.min_version = min_version
        super(Column, self).__init__(column_type)

    def __repr__(self):
        return "<{}.{} {} {}>".format(self.__class__.__module__,
                                      self.__class__.__name__,
                                      self.icat_id,
                                      self.icat_key)

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
        return "'{}'".format(data)


class String(ColumnType):

    @staticmethod
    def to_python(string):
        return string

    @staticmethod
    def to_irods(data):
        try:
            # Convert to Unicode string (aka decode)
            data = six.text_type(data, 'utf-8', 'replace')
        except TypeError:
            # Some strings are already Unicode so they do not need decoding
            pass
        return u"'{}'".format(data)


class DateTime(ColumnType):

    @staticmethod
    def to_python(string):
        return datetime.utcfromtimestamp(int(string))

    @staticmethod
    def to_irods(data):
        try:
            return "'{:0>11}'".format(timegm(data.utctimetuple()))
        except AttributeError:
            return "'{}'".format(data)
