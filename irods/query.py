import logging
from models import Base
from column import Column

class Query(object):
    def __init__(self, sess, *args):
        logging.debug(args)
        self.sess = sess
        columns = set()
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, Base):
                for col in arg._columns:
                    columns.add(col)
            elif isinstance(arg, Column):
                columns.add(arg)
            else:
                raise TypeError("Arguments must be models or columns")

        self.columns = dict([(x,1) for x in columns])
        logging.debug(self.columns)

    def filter(*args):
        pass

    def order_by(*args):
        pass

    def limit(max):
        pass

    def all():
        pass

    def one():
        pass

    def __getitem__(self, val):
        pass
