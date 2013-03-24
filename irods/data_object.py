from models import DataObject

class iRODSDataObject(object):
    def __init__(self, result=None):
        if result:
            self.id = result[DataObject.id]
            self.name = result[DataObject.name]
