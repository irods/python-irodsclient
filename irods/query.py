import logging
from models import Model
from column import Column, Keyword
from message import (IntegerIntegerMap, IntegerStringMap, StringStringMap, 
    GenQueryRequest, GenQueryResponse, empty_gen_query_out,
    iRODSMessage)
from api_number import api_number
from exception import CAT_NO_ROWS_FOUND, MultipleResultsFound, NoResultFound
from results import ResultSet

class Query(object):

    def __init__(self, sess, *args, **kwargs):
        self.sess = sess
        self.columns = kwargs['columns'] if 'columns' in kwargs else {}
        self.criteria = kwargs['criteria'] if 'criteria' in kwargs else []
        self._limit = kwargs['limit'] if 'limit' in kwargs else -1

        for arg in args:
            if isinstance(arg, type) and issubclass(arg, Model):
                for col in arg._columns:
                    self.columns[col] = 1
            elif isinstance(arg, Column):
                self.columns[arg] = 1
            else:
                raise TypeError("Arguments must be models or columns")

    def filter(self, *criteria):
        new_q = Query(self.sess, columns=self.columns, criteria=self.criteria + list(criteria))
        return new_q

    def order_by(*args):
        pass

    def limit(self, limit):
        new_q = Query(self.sess, columns=self.columns, criteria=self.criteria, limit=limit)
        return new_q

    def _select_message(self):
        dct = dict([(column.icat_id, value) for (column, value) in self.columns.iteritems()])
        return IntegerIntegerMap(dct)

    #todo store criterion for columns and criterion for keywords in seaparate lists
    def _conds_message(self):
        dct = dict([
            (criterion.query_key.icat_id, criterion.op + ' ' + criterion.value) 
            for criterion in self.criteria 
            if isinstance(criterion.query_key, Column)
        ])
        return IntegerStringMap(dct)

    def _kw_message(self):
        dct = dict([
            (criterion.query_key.icat_key, criterion.op + ' ' + criterion.value) 
            for criterion in self.criteria 
            if isinstance(criterion.query_key, Keyword)
        ])
        return StringStringMap(dct)

    def _message(self):
        max_rows = 500 if self._limit == -1 else self._limit
        args = {
            'maxRows': max_rows,
            'continueInx': 0,
            'partialStartIndex': 0,
            'options': 0,
            'KeyValPair_PI': self._kw_message(),
            'InxIvalPair_PI': self._select_message(),
            'InxValPair_PI': self._conds_message()
        }
        return GenQueryRequest(**args)

    def execute(self):
        message_body = self._message()
        message = iRODSMessage('RODS_API_REQ', msg=message_body, int_info=api_number['GEN_QUERY_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            try:
                result_message = conn.recv()
                results = result_message.get_main_message(GenQueryResponse)
                result_set = ResultSet(results)
            except CAT_NO_ROWS_FOUND:
                result_set = ResultSet(empty_gen_query_out(self.columns.keys())) 
        return result_set
        
    def all(self):
        return self.execute()

    def one(self):
        results = self.execute()
        if not len(results):
            raise NoResultFound()
        if len(results) > 1:
            raise MultipleResultsFound()
        return results[0]

    def first(self):
        query = self.limit(1)
        results = query.execute()
        if not len(results):
            return None
        else:
            return results[0]

    def __getitem__(self, val):
        pass
