import logging
from models import Base
from column import Column, Keyword
from message import InxIvalPair, InxValPair, KeyValPair, GenQueryInp

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

    #todo store criterion for columns and criterion for keywords in seaparate lists
    def _conds_message(self):
        dct = dict([
            (criterion.query_key.icat_id, criterion.op + ' ' + criterion.value) 
            for criterion in self.criteria 
            if isinstance(criterion.query_key, Column)
        ])
        return InxValPair(dct)

    def _kw_message(self):
        dct = dict([
            (criterion.query_key.icat_key, criterion.op + ' ' + criterion.value) 
            for criterion in self.criteria 
            if isinstance(criterion.query_key, Keyword)
        ])
        return KeyValPair(dct)

    def _message(self):
        args = {
            'limit': 500,
            'cond_kw': self._kw_message().pack(),
            'select': self._select_message().pack(),
            'cond': self._conds_message().pack(),
            'options': 33,
            'offset': 0,
            'continue_index': 0,
        }
        return GenQueryInp(**args)
        
    def all(self):
        return self.sess.execute_query(self)

    def one(self):
        pass

    def __getitem__(self, val):
        pass
