import logging
from models import ModelBase

class ResultSet(object):
    def __init__(self, raw):
        #self._raw = raw #gen query out object
        self.length = raw.rowCnt

        col_length = raw.attriCnt
        self.cols = raw.SqlResult_PI[:col_length]

        self.rows = [self._format_row(i) for i in range(self.length)]

    def __str__(self):
        columns = [(col, max(len(str(ModelBase.columns[col.attriInx].icat_key)), max([len(str(x)) for x in col.value]))) for col in self.cols]
        separator = "-+-".join(["-" * width for (_, width) in columns])
        header = " | ".join([str(ModelBase.columns[col.attriInx].icat_key).ljust(width) for (col, width) in columns])
        rows = "\n".join([" | ".join( [str(columns[j][0].value[i]).ljust(columns[j][1]) for j in range(len(columns)) ]) for i in range(self.length) ])
        return "\n".join([separator, header, separator, rows, separator])

    def _format_row(self, index):
        values = [(col, col.value[index]) for col in self.cols]

        def format(attribute_index, value):
            col = ModelBase.columns[attribute_index]
            return (col, col.type.to_python(value))
            
        return dict([format(col.attriInx, value) for col, value in values])

    def __getitem__(self, index):
        return self.rows.__getitem__(index)

    def __iter__(self):
        return self.rows.__iter__()
