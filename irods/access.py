import collections

class iRODSAccess(object):

    codes = { key:value for key,value in dict(  # copied from iRODS server code:
        null                 = 1000,            # server/core/include/irods/catalog_utilities.hpp
        execute              = 1010,
        read_annotation      = 1020,
        read_system_metadata = 1030,
        read_metadata        = 1040,
        read_object          = 1050,
        write_annotation     = 1060,
        create_metadata      = 1070,
        modify_metadata      = 1080,
        delete_metadata      = 1090,
        administer_object    = 1100,
        create_object        = 1110,
        modify_object        = 1120,
        delete_object        = 1130,
        create_token         = 1140,
        delete_token         = 1150,
        curate               = 1160,
        own                  = 1200
    ).items() if key in (
            # These are copied from ichmod help text.
            'own',
            'delete_object',
            'write', 'modify_object',
            'create_object',
            'delete_metadata',
            'modify_metadata',
            'create_metadata',
            'read', 'read_object',
            'read_metadata',
            'null'
        )
    }

    strings = collections.OrderedDict(sorted((number,string) for string,number in codes.items()))

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
