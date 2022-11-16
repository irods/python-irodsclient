class iRODSAccess(object):

    def __init__(self, access_name, path, user_name='', user_zone='', user_type=None):
        self.access_name = access_name
        self.path = path
        self.user_name = user_name
        self.user_zone = user_zone
        self.user_type = user_type

    def __repr__(self):
        object_dict = vars(self)
        access_name = self.access_name.replace(' ','_')
        user_type_hint = ("({user_type})" if object_dict.get('user_type') is not None else "").format(**object_dict)
        return "<iRODSAccess {0} {path} {user_name}{1} {user_zone}>".format(access_name,
                                                                            user_type_hint,
                                                                            **object_dict)
