class Column(object):
    def __init__(self, type, icat_key, icat_id):
        self.type = type
        self.icat_key = icat_key
        self.icat_id = icat_id

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
