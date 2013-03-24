from models import Collection

class iRODSCollection(object):
    def __init__(self, result=None):
        if result:
            self.id = result[Collection.id]
            self.name = result[Collection.name]
