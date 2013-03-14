from os.path import basename

class iRODSFile(object):
    def __init__(self, conn, path):
        self._conn = conn
        self._meta = None
        self.path = path
        self.name = basename(self.path)

    def exists():
        return False

class iRODSDataObject(iRODSFile):
    def __init__(self, conn, path):
        iRODSFile.__init__(self, conn, path)

class iRODSCollection(iRODSFile):
    def __init__(self, conn, path):
        iRODSFile.__init__(self, conn, path)

    def get_subcollections(self):
        subcollections = self._file.getSubCollections()
        return map(lambda dir_name: DSCollection(self._conn, self.path + "/" + dir_name), subcollections)

    def get_objects(self):
        objects = self._file.getObjects()
        return map(lambda obj: DSDataObject(self._conn, self.path + "/" + obj[0]), objects)
