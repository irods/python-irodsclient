import collections
import copy
from irods.collection import iRODSCollection
from irods.data_object import iRODSDataObject
from irods.path import iRODSPath


class _Access_LookupMeta(type):
    def __getitem__(self, key):
        return self.codes[key]

    def keys(self):
        return list(self.codes.keys())

    def values(self):
        return list(self.codes[k] for k in self.codes.keys())

    def items(self):
        return list(zip(self.keys(), self.values()))


class iRODSAccess(metaclass=_Access_LookupMeta):

    @classmethod
    def to_int(cls, key):
        return cls.codes[key]

    @classmethod
    def to_string(cls, key):
        return cls.strings[key]

    codes = collections.OrderedDict(
        (key_, value_)
        for key_, value_ in sorted(
            dict(
                # copied from iRODS source code in
                #   ./server/core/include/irods/catalog_utilities.hpp:
                null=1000,
                execute=1010,
                read_annotation=1020,
                read_system_metadata=1030,
                read_metadata=1040,
                read_object=1050,
                write_annotation=1060,
                create_metadata=1070,
                modify_metadata=1080,
                delete_metadata=1090,
                administer_object=1100,
                create_object=1110,
                modify_object=1120,
                delete_object=1130,
                create_token=1140,
                delete_token=1150,
                curate=1160,
                own=1200,
            ).items(),
            key=lambda _: _[1],
        )
        if key_
        in (
            # These are copied from ichmod help text.
            "own",
            "delete_object",
            "write",
            "modify_object",
            "create_object",
            "delete_metadata",
            "modify_metadata",
            "create_metadata",
            "read",
            "read_object",
            "read_metadata",
            "null",
        )
    )

    strings = collections.OrderedDict(
        (number, string) for string, number in codes.items()
    )

    def __init__(self, access_name, path, user_name="", user_zone="", user_type=None):
        self.access_name = access_name
        if isinstance(path, (iRODSCollection, iRODSDataObject)):
            self.path = path.path
        elif isinstance(path, str):
            # This should cover irods.path.iRODSPath as well as it is a descendant type of str.
            self.path = path
        else:
            raise TypeError(
                "'path' parameter must be of type 'str', 'irods.collection.iRODSCollection', "
                "'irods.data_object.iRODSDataObject', or 'irods.path.iRODSPath'."
            )
        self.user_name = user_name
        self.user_zone = user_zone
        self.user_type = user_type

    def __eq__(self, other):
        return (
            self.access_name == other.access_name
            and iRODSPath(self.path) == iRODSPath(other.path)
            and self.user_name == other.user_name
            and self.user_zone == other.user_zone
        )

    def __hash__(self):
        return hash(
            (self.access_name, iRODSPath(self.path), self.user_name, self.user_zone)
        )

    def copy(self, decanonicalize=False):
        other = copy.deepcopy(self)
        if decanonicalize:
            replacement_string = {
                "read object": "read",
                "read_object": "read",
                "modify object": "write",
                "modify_object": "write",
            }.get(self.access_name)
            other.access_name = (
                replacement_string
                if replacement_string is not None
                else self.access_name
            )
        return other

    def __repr__(self):
        object_dict = vars(self)
        access_name = self.access_name.replace(" ", "_")
        user_type_hint = (
            "({user_type})" if object_dict.get("user_type") is not None else ""
        ).format(**object_dict)
        return f"<iRODSAccess {access_name} {self.path} {self.user_name}{user_type_hint} {self.user_zone}>"


class _iRODSAccess_pre_4_3_0(iRODSAccess):
    codes = collections.OrderedDict(
        (key.replace("_", " "), value)
        for key, value in iRODSAccess.codes.items()
        if key in ("own", "write", "modify_object", "read", "read_object", "null")
    )
    strings = collections.OrderedDict(
        (number, string) for string, number in codes.items()
    )
