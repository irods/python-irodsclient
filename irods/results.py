from models import ModelBase

class ResultSet(object):
    def __init__(self, raw):
        self._raw = raw #gen query out object

    def __iter__(self):
        return ResultSetIterator(self)

    def __str__(self):
        columns = [(col, max(len(str(col.attribute_index)), max([len(x) for x in col.values]))) for col in self._raw.sql_results]
        header = " | ".join([str(col.attribute_index).ljust(width) for (col, width) in columns])
        rows = "\n".join([" | ".join( [columns[j][0].values[i].ljust(columns[j][1]) for j in range(len(columns)) ]) for i in range(self._raw.row_count) ])
        return header + "\n" + rows + "\n"

class ResultSetIterator(object):
    def __init__(self, results):
        self.results = results._raw
        self.length = results._raw.row_count
        self.index = 0

    def __iter__(self):
        return self

    def next(self):
        if self.index < self.length - 1:
            values = [(col, col.values[self.index]) for col in self.results.sql_results]
            self.index += 1

            def format(attribute_index, value):
                col = ModelBase.columns[attribute_index]
                return (col, col.type.to_python(value))
                
            return dict([format(col.attribute_index, value) for col, value in values])
        else:
            raise StopIteration
