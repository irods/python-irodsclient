from irods.models import User

class iRODSUser(object):
    def __init__(self, manager, result=None):
        self.manager = manager
        if result:
            self.id = result[User.id]
            self.name = result[User.name]
            self.type = result[User.type]
            self.zone = result[User.zone]
        self._meta = None

    def __repr__(self):
        return "<iRODSUser %d %s %s %s>" % (self.id, self.name, self.type, self.zone)
