class ResultSet(object):
    def __init__(self, raw):
        self._raw = raw #gen query out object

    def __str__(self):
        columns = [(col, max(len(str(col.attribute_index)), max([len(x) for x in col.values]))) for col in self._raw.sql_results]
        header = " | ".join([str(col.attribute_index).ljust(width) for (col, width) in columns])
        rows = "\n".join([" | ".join( [columns[j][0].values[i].ljust(columns[j][1]) for j in range(len(columns)) ]) for i in range(self._raw.row_count) ])
        return header + "\n" + rows + "\n"
