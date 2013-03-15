import logging
from models import Base
from column import Column
from message import InxIvalPair

class Query(object):

    def __init__(self, sess, *args, **kwargs):
        self.sess = sess
        self.columns = kwargs['columns'] if 'columns' in kwargs else {}
        self.criteria = kwargs['criteria'] if 'criteria' in kwargs else []

        for arg in args:
            if isinstance(arg, type) and issubclass(arg, Base):
                for col in arg._columns:
                    self.columns[col] = 1
            elif isinstance(arg, Column):
                self.columns[arg] = 1
            else:
                raise TypeError("Arguments must be models or columns")

    def filter(self, criterion):
        new_q = Query(self.sess, columns=self.columns, criteria=self.criteria + [criterion])
        return new_q

    def order_by(*args):
        pass

    def limit(max):
        pass

    def _select_message(self):
        dct = dict([(column.icat_id, value) for (column, value) in self.columns.iteritems()])
        return InxIvalPair(dct)

    def _conds_message(self):
        pass

    def _kw_message(self):
        pass
        
    def all():
        pass

    def one():
        pass

    def __getitem__(self, val):
        pass
