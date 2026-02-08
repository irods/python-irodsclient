import base64
import copy


class iRODSMeta:

    def _to_column_triple(self):
        return (self.name ,self.forward_translate(self.value)) + (
            ('',) if not self.units else (self.forward_translate(self.units),)
        )

    def _from_column_triple(self, name, value, units, **kw):
        self.__low_level_init(
            name,
            self.reverse_translate(value),
            units=None if not units else self.reverse_translate(units),
            **kw
        )
        return self

    reverse_translate = forward_translate = staticmethod(lambda _: _)

    INIT_KW_ARGS = ['units', 'avu_id', 'create_time', 'modify_time']

    def __init__(
        self, name, value, /, units=None, *, avu_id=None, create_time=None, modify_time=None,
    ):
        # Defer initialization for iRODSMeta(attribute,value,...) if neither attribute nor value is True under
        # a 'bool' transformation.  In so doing we streamline initialization for iRODSMeta (and any subclasses)
        # for alternatively populating via _from_column_triple(...).
        # This is the pathway for allowing user-defined encodings of the iRODSMeta (byte-)string AVU components.
        if name or value:
            # Note: calling locals() inside the dict comprehension would not access variables in this frame.
            local_vars = locals()
            kw = {name: local_vars.get(name) for name in self.INIT_KW_ARGS}
            self.__low_level_init(name, value, **kw)

    def __low_level_init(self, name, value, **kw):
        self.name = name
        self.value = value
        for attr in self.INIT_KW_ARGS:
            setattr(self, attr, kw.get(attr))

    def __eq__(self, other):
        return tuple(self) == tuple(other)

    def __iter__(self):
        yield self.name
        yield self.value
        if self.units:
            yield self.units

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.avu_id} {self.name} {self.value} {self.units}>"

    def __hash__(self):
        return hash(tuple(self))


class iRODSBinOrStringMeta(iRODSMeta):
    @staticmethod
    def reverse_translate(value):
        """Translate an AVU field from its iRODS object-database form into the client representation of that field."""
        return value if value[0] != '\\' else base64.decodebytes(value[1:].encode('utf8'))

    @staticmethod
    def forward_translate(value):
        """Translate an AVU field from the form it takes in the client, into an iRODS object-database compatible form."""
        return b'\\' + base64.encodebytes(value).strip() if isinstance(value,(bytes,bytearray)) else value


class BadAVUOperationKeyword(Exception):
    pass


class BadAVUOperationValue(Exception):
    pass


class AVUOperation(dict):

    @property
    def operation(self):
        return self["operation"]

    @operation.setter
    def operation(self, Oper):
        self._check_operation(Oper)
        self["operation"] = Oper

    @property
    def avu(self):
        return self["avu"]

    @avu.setter
    def avu(self, newAVU):
        self._check_avu(newAVU)
        self["avu"] = newAVU

    def _check_avu(self, avu_param):
        if not isinstance(avu_param, iRODSMeta):
            error_msg = (
                "Nonconforming avu {!r} of type {}; must be an iRODSMeta."
                "".format(avu_param, type(avu_param).__name__)
            )
            raise BadAVUOperationValue(error_msg)

    def _check_operation(self, operation):
        if operation not in ("add", "remove"):
            error_msg = (
                "Nonconforming operation {!r}; must be 'add' or 'remove'.".format(
                    operation
                )
            )
            raise BadAVUOperationValue(error_msg)

    def __init__(self, operation, avu, **kw):
        """Constructor:
        AVUOperation( operation = opstr,  # where opstr is "add" or "remove"
                      avu = metadata )    # where metadata is an irods.meta.iRODSMeta instance
        """
        super(AVUOperation, self).__init__()
        self._check_operation(operation)
        self._check_avu(avu)
        if kw:
            raise BadAVUOperationKeyword(
                """Nonconforming keyword (s) {}.""".format(list(kw.keys()))
            )
        for atr in ("operation", "avu"):
            setattr(self, atr, locals()[atr])


class iRODSMetaCollection:
    def __getattr__(self,n):
        from irods.manager.metadata_manager import _default_MetadataManager_opts
        if n in _default_MetadataManager_opts:
            return self._manager._opts[n]
        raise AttributeError

    def __call__(self, **opts):
        """
        Optional parameters in **opts are:

        admin (default: False): apply ADMIN_KW to future metadata operations.
        timestamps (default: False): attach (ctime,mtime) timestamp attributes to AVUs received from iRODS.
        """
        x = copy.copy(self)
        x._manager = (x._manager)(**opts)
        x._reset_metadata()
        return x

    def __init__(self, manager, model_cls, path):
        self._manager = manager
        self._model_cls = model_cls
        self._path = path
        self._reset_metadata()

    def _reset_metadata(self):
        m = self._manager
        if not hasattr(self, "_meta"):
            self._meta = m.get(None, "")
        if m._opts.setdefault('reload', True):
            self._meta = m.get(self._model_cls, self._path)

    def get_all(self, key):
        """
        Returns a list of iRODSMeta associated with a given key
        """
        if isinstance(key, bytes):
            key = key.decode("utf8")
        if not isinstance(key, str):
            raise TypeError
        return [m for m in self._meta if m.name == key]

    def get_one(self, key):
        """
        Returns the iRODSMeta defined for a key. If there are none,
        or if there are more than one defined, raises KeyError
        """
        values = self.get_all(key)
        if not values:
            raise KeyError
        if len(values) > 1:
            raise KeyError
        return values[0]

    def _get_meta(self, *args):
        if not len(args):
            raise ValueError("Must specify an iRODSMeta object or key, value, units)")
        return args[0] if len(args) == 1 else self._manager._opts['iRODSMeta_type'](*args)

    def apply_atomic_operations(self, *avu_ops):
        self._manager.apply_atomic_operations(self._model_cls, self._path, *avu_ops)
        self._reset_metadata()

    def set(self, *args, **opts):
        """
        Set as iRODSMeta to a key
        """
        meta = self._get_meta(*args)
        self._manager.set(self._model_cls, self._path, meta, **opts)
        self._reset_metadata()

    def add(self, *args, **opts):
        """
        Add as iRODSMeta to a key
        """
        meta = self._get_meta(*args)
        self._manager.add(self._model_cls, self._path, meta, **opts)
        self._reset_metadata()

    def remove(self, *args, **opts):
        """
        Removes an iRODSMeta
        """
        meta = self._get_meta(*args)
        self._manager.remove(self._model_cls, self._path, meta, **opts)
        self._reset_metadata()

    def items(self):
        """
        Returns a list of iRODSMeta
        """
        return self._meta

    def keys(self):
        """
        Return a list of keys. Duplicates preserved
        """
        return [m.name for m in self._meta]

    def __len__(self):
        return len(self._meta)

    def __getitem__(self, key):
        """
        Returns the first iRODSMeta defined on key. Order is
        undefined. Use get_one() or get_all() instead
        """
        values = self.get_all(key)
        if not values:
            raise KeyError
        return values[0]

    def __setitem__(self, key, meta):
        """
        Deletes all existing values associated with a given key and associates
        the key with a single iRODSMeta tuple
        """
        self._delete_all_values(key)
        self.add(meta)

    def _delete_all_values(self, key):
        for meta in self.get_all(key):
            self.remove(meta)

    def __delitem__(self, key):
        """
        Deletes all existing values associated with a given key
        """
        if not isinstance(key, str):
            raise TypeError
        self._delete_all_values(key)
        self._reset_metadata()

    def __contains__(self, key):
        if not isinstance(key, str):
            raise TypeError
        values = self.get_all(key)
        return len(values) > 0

    def remove_all(self, **opts):
        for meta in self._meta:
            self._manager.remove(self._model_cls, self._path, meta, **opts)
        self._reset_metadata()
