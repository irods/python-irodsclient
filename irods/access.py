class iRODSAccess(object):
    def __init__(self, name, user_id, data_id, user_name=None):
        self.name = name
        self.user_id = user_id
        self.data_id = data_id
        self.user_name = user_name

    def __repr__(self):
        return "<iRODSAccess {name} {user_id} {data_id}>".format(name=self.name, user_id=str(self.user_id), data_id=str(self.data_id))

    @property
    def __dict__(self):
        return {
            'name': self.name,
            'user_id': self.user_id,
            'data_id': self.data_id,
            'user_name': self.user_name
        }
