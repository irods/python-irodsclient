import logging
from models import Base
from column import Column

class Query(object):

    def __init__(self, sess, *args):
        self.sess = sess
        self.columns = {}
        self.criteria = []

        logging.debug(args)
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, Base):
                for col in arg._columns:
                    self.columns[col] = 1
            elif isinstance(arg, Column):
                self.columns[arg] = 1
            else:
                raise TypeError("Arguments must be models or columns")

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
