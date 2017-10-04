from __future__ import absolute_import
from prettytable import PrettyTable

from irods.models import ModelBase
from six.moves import range


class ResultSet(object):

    def __init__(self, raw):
        self.length = raw.rowCnt
        col_length = raw.attriCnt
        self.cols = raw.SqlResult_PI[:col_length]
        self.rows = [self._format_row(i) for i in range(self.length)]
        try:
            self.continue_index = raw.continueInx
        except KeyError:
            self.continue_index = 0

    def __str__(self):
        table = PrettyTable()
        for col in self.cols:
            table.add_column(
                ModelBase.columns[col.attriInx].icat_key, col.value)
        table.align = 'l'
        return table.get_string()

    def get_html_string(self, *args, **kwargs):
        table = PrettyTable()
        for col in self.cols:
            table.add_column(
                ModelBase.columns[col.attriInx].icat_key, col.value)
        table.align = 'l'
        return table.get_html_string(*args, **kwargs)

    @staticmethod
    def _format_attribute(attribute_index, value):
        col = ModelBase.columns[attribute_index]
        try:
            return (col, col.column_type.to_python(value))
        except (TypeError, ValueError):
            return (col, value)

    def _format_row(self, index):
        values = [(col, col.value[index]) for col in self.cols]
        return dict([self._format_attribute(col.attriInx, value) for col, value in values])

    def __getitem__(self, index):
        return self.rows.__getitem__(index)

    def __iter__(self):
        return self.rows.__iter__()

    def __len__(self):
        return self.length

    # For testing. Might go somewhere else...
    def has_value(self, value):
        found = False

        for row in self.rows:
            if value in list(row.values()):
                found = True

        return found


class SpecificQueryResultSet(ResultSet):

    def __init__(self, raw, columns=None):
        self._query_columns = columns
        super(SpecificQueryResultSet, self).__init__(raw)


    def _format_row(self, index):
        values = [col.value[index] for col in self.cols]

        formatted_row = {}

        for i, value in enumerate(values):
            try:
                column = self._query_columns[i]
                result_key = column
            except TypeError:
                column = ModelBase.columns[0] # SpecificQueryResult.value
                result_key = i

            try:
                formatted_value = column.column_type.to_python(value)
            except (TypeError, ValueError):
                formatted_value = value

            formatted_row[result_key] = formatted_value

        return formatted_row
