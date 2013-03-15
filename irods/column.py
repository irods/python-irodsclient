class Column(object):
    def __init__(self, type, icat_key, icat_id):
        self.type = type
        self.icat_key = icat_key
        self.icat_id = icat_id

    def __lt__(self, other):
        return Criterion('<', self, other)

    def __le__(self, other):
        return Criterion('<=', self, other)

    def __eq__(self, other):
        return Criterion('=', self, other)

    def __ne__(self, other):
        return Criterion('!=', self, other)

    def __gt__(self, other):
        return Criterion('>', self, other)

    def __ge__(self, other):
        return Criterion('>=', self, other)

class Criterion(object):
    def __init__(self, op, col, value):
        self.op = op
        self.column = col
        self.value = value
        
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
