from irods.models import Resource

class iRODSResource(object):
    def __init__(self, manager, result=None):
        self.manager = manager
        if result:
            self.id = result[Resource.id]
            self.name = result[Resource.name]
            self.zone_name = result[Resource.zone_name]
            self.type = result[Resource.type]
            self.class_name = result[Resource.class_name]
            self.location = result[Resource.location]
            self.vault_path = result[Resource.vault_path]
        self._meta = None

    def __repr__(self):
        return "<iRODSResource {0} {1} {2} {3} {4} {5} {6}>".format(self.id, self.name, self.zone_name, 
                                                                    self.type, self.class_name, self.location, self.vault_path)
