class iRODSAccess(object):
    def __init__(self, access_name, user_id, data_id, user_name=None):
        self.access_name = access_name
        self.user_id = user_id
        self.data_id = data_id
        self.user_name = user_name

    def __repr__(self):
        return "<iRODSAccess {access_name} {user_id} {data_id}>".format(**vars(self))
