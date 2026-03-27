import collections
import copy
import warnings

from irods.collection import iRODSCollection
from irods.data_object import iRODSDataObject

_permissions = (
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


class _Access_LookupMeta(type):
    @staticmethod
    def _codes():
        return collections.OrderedDict(
            (key_, value_)
            for key_, value_ in sorted(
                {
                    # adapted from iRODS source code in
                    #   ./server/core/include/irods/catalog_utilities.hpp:
                    "null": 1000,
                    "execute": 1010,
                    "read_annotation": 1020,
                    "read_system_metadata": 1030,
                    "read_metadata": 1040,
                    "read_object": 1050,
                    "write_annotation": 1060,
                    "create_metadata": 1070,
                    "modify_metadata": 1080,
                    "delete_metadata": 1090,
                    "administer_object": 1100,
                    "create_object": 1110,
                    "modify_object": 1120,
                    "delete_object": 1130,
                    "create_token": 1140,
                    "delete_token": 1150,
                    "curate": 1160,
                    "own": 1200,
                }.items(),
                key=lambda _: _[1],
            )
            if key_ in _permissions
        )

    @property
    def codes(cls):
        return cls._codes()

    @property
    def strings(cls):
        return collections.OrderedDict((number, string) for string, number in cls._codes().items())

    def __getitem__(self, key):
        return self.codes[key]

    def keys(self):
        return list(self.codes.keys())

    def values(self):
        return list(self.codes[k] for k in self.codes.keys())

    def items(self):
        return list(zip(self.keys(), self.values()))


class _iRODSAccess_base:
    @classmethod
    def to_int(cls, key):
        return cls.codes[key]

    @classmethod
    def to_string(cls, key):
        return cls.strings[key]

    def __init__(self, access_name, path, user_name, user_zone, user_type):
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

    def __lt__(self, other):
        return (self.access_name, self.user_name, self.user_zone, str(self.path)) < (
            other.access_name,
            other.user_name,
            other.user_zone,
            str(other.path),
        )

    def __eq__(self, other):
        return (
            self.access_name == other.access_name
            and str(self.path) == str(other.path)
            and self.user_name == other.user_name
            and self.user_zone == other.user_zone
        )

    def __hash__(self):
        return hash((self.access_name, str(self.path), self.user_name, self.user_zone))

    def normalize(self, local_zone=""):
        """
        Create a normalized version of the object for comparison in sorting or determining equivalence.

        Args:
            local_zone: the name of the home zone, if any, in which client user directly authenticates.
                The purpose is zone name normalization; if this parameter is a nonzero-length string which
                matches the zone_name in the source object, the copy will contain a null zone_name field.

        Returns:
            The normalized copy of the source object.  In practice, this will be an ACLOperation or iRODSAccess
            object, according to the type of the source object.
        """
        normalized_form = self.copy(decanonicalize=-1, implied_zone=local_zone)
        normalized_form.path = ""
        return normalized_form

    def copy(self, decanonicalize=False, implied_zone=''):
        """
        Create a copy of the object, possibly in a normalized form.

        Args:
            decanonicalize: Whether to modify the access_name field to a more human-readable form
                (when 1 or True) or a more standard form (when -1).  If the former, then a more
                organic style is favored, i.e.  "read" and "write".  If the latter, the new
                access_name will be more machine-friendly for operators __lt__ (for sorting) and
                __eq__ (for equivalence or use with 'in').  If equal to 0 (or False), no adjustment
                is done.
            implied_zone: If a nonzero-length name, compare this against the zone_name field of the
                old object, and if they match, force the zone_name to zero-length in the new object.

        Returns:
            A copy of the invoking object, normalized if requested.

        Raises:
            RuntimeError: if decanonicalize parameter is not one of {-1,0,False,1,True}.
        """
        other = copy.deepcopy(self)

        access_name = self.access_name

        if decanonicalize == 1:
            if (
                new_access_name := {
                    "read object": "read",
                    "read_object": "read",
                    "modify object": "write",
                    "modify_object": "write",
                }.get(access_name)
            ) is not None:
                access_name = new_access_name
        elif decanonicalize == -1:
            # Canonicalize, ie. change out old access_name for an unambiguous "standard" value.
            access_name = access_name.replace(" ", "_")
            if (
                new_access_name := {
                    "read": "read_object",
                    "write": "modify_object",
                }.get(access_name)
            ) is not None:
                access_name = new_access_name
        elif decanonicalize == 0:
            pass
        else:
            msg = "Improper value for 'decanonicalize' parameter"
            raise RuntimeError(msg)

        other.access_name = access_name

        # Useful if we wish to force an explicitly specified local zone to an implicit zone spec in the copy, for
        # equality testing:
        if '' != implied_zone == other.user_zone:
            other.user_zone = ''

        return other

    def __repr__(self):
        object_dict = vars(self)
        access_name = self.access_name.replace(" ", "_")
        user_type_hint = ("({user_type})" if object_dict.get("user_type") is not None else "").format(**object_dict)
        return f"<iRODSAccess {access_name} {self.path} {self.user_name}{user_type_hint} {self.user_zone}>"


class iRODSAccess(_iRODSAccess_base, metaclass=_Access_LookupMeta):
    """
    Represents an ACL in iRODS.

    An instance of this class functions as a data container to convey information to the iRODS
    server (in the `set` call) and back again to the client again (in the `get` call).
    """

    def __init__(self, access_name, path, user_name="", user_zone="", user_type=None):  # noqa: D107
        self.codes = self.__class__.codes
        self.strings = self.__class__.strings
        super().__init__(access_name, path, user_name, user_zone, user_type)


class ACLOperation(iRODSAccess):
    """
    Represents an operation to be performed in iRODS' atomic ACL api.

    Similar to its base class, iRODSAccess, this class names an ACL to be set on an object.
    It differs, however, in that it forgoes option to store a logical object path.  (In the atomic
    API call, there is always a single logical path to which all such operations apply, thus
    it is appropriate that the path parameter is in a location separate from the operations.)
    """  # noqa: D400

    # ruff: noqa: D105 on

    def __init__(self, access_name: str, user_name: str = "", user_zone: str = ""):  # noqa: D107
        super().__init__(
            access_name=access_name,
            path="",
            user_name=user_name,
            user_zone=user_zone,
        )

    def __eq__(self, other):
        return (
            self.access_name,
            self.user_name,
            self.user_zone,
        ) == (
            other.access_name,
            other.user_name,
            other.user_zone,
        )

    def __hash__(self):

        # Hash in a way consistent with an iRODSAccess having path "".
        return hash((
            self.access_name,
            "",  # path
            self.user_name,
            self.user_zone,
        ))

    def __lt__(self, other):
        return (
            self.access_name,
            self.user_name,
            self.user_zone,
        ) < (
            other.access_name,
            other.user_name,
            other.user_zone,
        )

    def __repr__(self):
        return f"<ACLOperation {self.access_name} {self.user_name} {self.user_zone}>"

    # ruff: noqa: D105 off


(
    _synonym_mapping := {
        "write": "modify_object",
        "read": "read_object",
    }
).update((key.replace("_", " "), key) for key in iRODSAccess.codes)


all_permissions = {
    **iRODSAccess.codes,
    **{key: iRODSAccess.codes[_synonym_mapping[key]] for key in _synonym_mapping},
}

canonical_permissions = {k: v for k, v in all_permissions.items() if ' ' not in k and k not in ('read', 'write')}


# ruff: noqa: RUF012 N801 SLF001 on


class _deprecated:
    class _iRODSAccess_pre_4_3_0(_iRODSAccess_base):
        codes = collections.OrderedDict(
            (key.replace("_", " "), value)
            for key, value in iRODSAccess.codes.items()
            if key in ("own", "write", "modify_object", "read", "read_object", "null")
        )
        strings = collections.OrderedDict((number, string) for string, number in codes.items())

        def __init__(self, *args, **kwargs):
            warnings.warn(
                "_iRODSAccess_pre_4_3_0 is deprecated and will be removed in "
                "a future version. Use iRODSAccess instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            super().__init__(*args, **kwargs)


_deprecated_names = {'_iRODSAccess_pre_4_3_0': _deprecated._iRODSAccess_pre_4_3_0}


def __getattr__(name):
    if name in _deprecated_names:
        warnings.warn(f"{name} is deprecated", DeprecationWarning, stacklevel=2)
        return _deprecated_names[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ruff: noqa: RUF012 N801 SLF001 off
