from models import ModelBase

class ResultSet(object):
    def __init__(self, raw):
        self._raw = raw #gen query out object
        self.length = raw.row_count
        self.rows = [self._format_row(i) for i in range(self.length)]

    def __str__(self):
        columns = [(col, max(len(str(col.attribute_index)), max([len(x) for x in col.values]))) for col in self._raw.sql_results]
        header = " | ".join([str(col.attribute_index).ljust(width) for (col, width) in columns])
        rows = "\n".join([" | ".join( [columns[j][0].values[i].ljust(columns[j][1]) for j in range(len(columns)) ]) for i in range(self._raw.row_count) ])
        return header + "\n" + rows + "\n"

    def _format_row(self, index):
        values = [(col, col.values[index]) for col in self._raw.sql_results]

        def format(attribute_index, value):
            col = ModelBase.columns[attribute_index]
            return (col, col.type.to_python(value))
            
        return dict([format(col.attribute_index, value) for col, value in values])

    def __getitem__(self, index):
        return self.rows.__getitem__(index)

    def __iter__(self):
        return self.rows.__iter__()
