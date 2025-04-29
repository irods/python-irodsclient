import ast
import collections
import contextlib
import copy
import io
import logging
import os
import re
import sys
import types

# Duplicate here for convenience
from .. import DEFAULT_CONFIG_PATH

logger = logging.getLogger(__name__)


class iRODSConfiguration:
    __slots__ = ()


def getter(category, setting):
    """A programmatic way of allowing the current value of the specified setting to be
    given indirectly (through an extra call indirection) as the default value of a parameter.

    Returns a lambda that, when called, will yield the setting's value. In the closure of
    that lambda, the Python builtin function globals() is used to access (in a read-only
    capacity) the namespace dict of the irods.client_configuration module.

    See the irods.manager.data_object_manager.DataObjectManager.open(...) method signature
    for a usage example.
    """
    return lambda: getattr(globals()[category], setting)


class iRODSConfigAliasMetaclass(type):
    def __new__(meta, name, bases, attrs):
        cls = type.__new__(meta, name, bases, attrs)
        cls.writeable_properties = tuple(
            k
            for k, v in attrs.items()
            if isinstance(v, property) and v.fset is not None
        )
        return cls


class ConnectionsProperties(iRODSConfiguration, metaclass=iRODSConfigAliasMetaclass):
    @property
    def xml_parser_default(self):
        from irods.message import get_default_XML_by_name

        return get_default_XML_by_name()

    @xml_parser_default.setter
    def xml_parser_default(self, str_value):
        from irods.message import set_default_XML_by_name

        return set_default_XML_by_name(str_value)

connections = ConnectionsProperties()

class ConfigurationError(BaseException): pass
class ConfigurationValueError(ValueError,ConfigurationError): pass

class Genquery1_Properties(iRODSConfiguration, metaclass=iRODSConfigAliasMetaclass):

    @property
    def irods_query_limit(self):
        import irods.query
        return irods.query.IRODS_QUERY_LIMIT

    @irods_query_limit.setter
    def irods_query_limit(self, target_value):
        import irods.query
        requested = int(target_value)

        if requested <= 0:
            raise ConfigurationValueError(f'Error setting IRODS_QUERY_LIMIT to [{requested}]. Use positive values only.')

        irods.query.IRODS_QUERY_LIMIT = requested

genquery1 = Genquery1_Properties()


# #############################################################################
#
# Classes for building client configuration categories
# (irods.client_configuration.data_objects is one such category):


class DataObjects(iRODSConfiguration):
    __slots__ = (
        "auto_close",
        "allow_redirect",
        "force_create_by_default",
        "force_put_by_default",
    )

    def __init__(self):

        # Setting it in the constructor lets the attribute be a
        # configurable one and allows a default value of False.
        #
        # Running following code will opt in to the the auto-closing
        # behavior for any data objects opened subsequently.
        #
        # >>> import irods.client_configuration as config
        # >>> irods.client_configuration.data_objects.auto_close = True

        self.auto_close = False
        self.allow_redirect = False

        self.force_create_by_default = True
        self.force_put_by_default = True


# #############################################################################
#
# Instantiations of client-configuration categories:

# The usage "irods.client_configuration.data_objects" reflects the commonly used
# manager name (session.data_objects) and is thus understood to influence the
# behavior of data objects.
#
# By design, valid configurable targets (e.g. auto_close) are limited to the names
# listed in the __slots__ member of the category class.

data_objects = DataObjects()


class LegacyAuth(iRODSConfiguration):
    __slots__ = ("pam", "force_legacy_auth")

    class Pam(iRODSConfiguration):
        __slots__ = (
            "time_to_live_in_hours",
            "password_for_auto_renew",
            "store_password_to_environment",
            "force_use_of_dedicated_pam_api",
        )

        def __init__(self):
            self.time_to_live_in_hours = (
                0  # -> We default to the server's TTL preference.
            )
            self.password_for_auto_renew = ""
            self.store_password_to_environment = False
            self.force_use_of_dedicated_pam_api = False

    def __init__(self):
        self.pam = self.Pam()
        self.force_legacy_auth = False


legacy_auth = LegacyAuth()


# Exposes the significant settable attributes of an iRODSConfiguration object:
def _config_names(root):
    slots = getattr(root, "__slots__", ())
    properties = getattr(root, "writeable_properties", ())
    return tuple(slots) + tuple(properties)


# Exposes one level of the configuration hierarchy from the given ("root") node:
def _var_items(root, leaf_flag=False):
    if leaf_flag:
        flag = lambda _: (_,)
    else:
        flag = lambda _: ()
    if isinstance(root, types.ModuleType):
        return [
            ((i, v) + flag(False))
            for i, v in vars(root).items()
            if isinstance(v, iRODSConfiguration)
        ]
    if isinstance(root, iRODSConfiguration):
        return [(i, getattr(root, i)) + flag(True) for i in _config_names(root)]
    return []


# Recurses through an entire configuration hierarchy:
def _var_items_as_generator(root=sys.modules[__name__], dotted=""):
    _v = _var_items(root, leaf_flag=True)
    for name, sub_node, is_config in _v:
        dn = dotted + ("." if dotted else "") + name
        yield dn, sub_node, is_config
        #       # TODO: (#480) When Python2 support is removed, we can instead use the simpler construction:
        #       yield from _var_items_as_generator(root = sub_node, dotted = dn)
        for _dotted, _root, _is_config in _var_items_as_generator(
            root=sub_node, dotted=dn
        ):
            yield _dotted, _root, _is_config


VarItemTuple = collections.namedtuple("VarItemTuple", ["dotted", "root", "is_config"])


def _var_item_tuples_as_generator(root=sys.modules[__name__]):
    for _ in _var_items_as_generator(root):
        yield VarItemTuple(*_)


def save(root=None, string="", file=""):
    """Save the current configuration.

    When called simply as save(), this function simply writes all client settings into
    a configuration file.

    The 'root' and 'string' parameters are not likely to be overridden when called from an
    application. They should usually only vary from the defaults when save() recurses into itself.
    However, for due explanation's sake: 'root' specifies at which subtree node to start writing,
    None denoting the top level; and 'string' specifies a prefix for the dotted prefix name,
    which should be empty for an invocation that references the settings' top level namespace.
    Both of these defaults are in effect when calling save() without explicit parameters.

    The configuration file path will normally be the value of DEFAULT_CONFIG_PATH,
    but this can be overridden by supplying a non-empty string in the 'file' parameter.
    """
    _file = None
    auto_close_settings = False
    try:
        if not file:
            from .. import get_settings_path

            file = get_settings_path()
        if isinstance(file, str):
            _file = open(file, "w")
            auto_close_settings = True
        else:
            _file = file  # assume file-like object if not a string
        if root is None:
            root = sys.modules[__name__]
        for k, v in _var_items(root):
            dotted_string = string + ("." if string else "") + k
            if isinstance(v, iRODSConfiguration):
                save(root=v, string=dotted_string, file=_file)
            else:
                print(dotted_string, repr(v), sep="\t\t", file=_file)
        return file
    finally:
        if _file and auto_close_settings:
            _file.close()


@contextlib.contextmanager
def loadlines(entries, common_root=sys.modules[__name__]):
    """Temporarily change the values for one or more settings in the PRC's configuration.  Useful for test code.

    Parameters:
        entries: list of dict objects of the form dict(setting="dotted.path.to.setting", value=<temp_value>).
        common_root: root point in configuration tree (best left to its default value).

    Sample usage:
    with loadlines(entries=[dict(setting='legacy_auth.pam.password_for_auto_renew',value='my-pam-password'),
                            dict(setting='legacy_auth.pam.store_password_to_environment',value=True)]):
        # ... test code for which the altered setting(s) should be in force
    """
    root_item = [("root", common_root)]
    entries_ = copy.deepcopy(entries)
    identity = lambda _: _
    try:
        # Load config values.
        entries_ = []
        for e in entries:
            e_ = dict(root_item + list(e.items()))
            L = []
            _load_config_line(eval_func=identity, return_old=L, **e_)
            e_["value"] = L[0]
            entries_.append(e_)
        yield
    finally:
        # Restore old values.
        for e_ in entries_:
            _load_config_line(eval_func=identity, **e_)


def _load_config_line(
    root, setting, value, return_old=None, eval_func=ast.literal_eval
):
    """Low-level utility function for loading a line of settings, with the option to return the old (displaced) value.

    The 'root' refers to the starting point in the configuration tree.  Its meaning is the same as in loadlines().
    The 'setting' is a string containing the dotted name for the configuration setting.
    The 'value' is the new value to be loaded.  This will be evaluated via 'eval_func' (see below).
    The 'return_old' is either None or a list which returns the displaced value back to the caller.
    The 'eval_func' is a function for making the supplied 'value' parameter into a Pythonic value to be assigned to the given 'setting'.
    """

    arr = [_.strip() for _ in setting.split(".")]
    loadexc = None
    # Compute the object referred to by the dotted name.
    try:
        attr = ""
        for i in filter(None, arr):
            if attr:
                root = getattr(root, attr)
            attr = i
        # Assign into the current setting of the dotted name (effectively <root>.<attr>)
        # using the loaded value.
        if attr:
            if isinstance(return_old, list):
                # Return, in the provided list, the old value of the setting.
                return_old.append(getattr(root, attr))
            return setattr(root, attr, eval_func(value))
    except Exception as e:
        loadexc = e

    # If we get this far, there's a problem loading the configuration setting.  Raise an exception or log it.
    error_message = (
        "Bad setting: root = {root!r}, setting = {setting!r}, value = {value!r}".format(
            **locals()
        )
    )
    if loadexc:
        error_message += " [{loadexc!r}]".format(**locals())
    if allow_config_load_errors:
        raise RuntimeError(error_message)
    else:
        logging.getLogger(__name__).log(logging.ERROR, "%s", error_message)


allow_config_load_errors = ast.literal_eval(
    os.environ.get("PYTHON_IRODSCLIENT_CONFIGURATION_LOAD_ERRORS_FATAL", "False")
)

# The following regular expression is used to match a configuration file line of the form:
# ---------------------------------------------------------------
#         <optional whitespace>
#  key:   <dotted-name specification>
#         <whitespace of length 1 or more>
#  value: <A Python value which can be given to ast.literal_eval(); e.g. 5, True, or 'some_string'>
#         <optional whitespace>

_key_value_pattern = re.compile(r"\s*(?P<key>\w+(\.\w+)+)\s+(?P<value>\S.*?)\s*$")


class _ConfigLoadError:
    """
    Exceptions that subclass this type can be thrown by the load() function if
    their classes are listed in the failure_modes parameter of that function.
    """


class NoConfigError(Exception, _ConfigLoadError):
    pass


class BadConfigError(Exception, _ConfigLoadError):
    pass


def load(
    root=None,
    file="",
    failure_modes=(),
    verify_only=False,
    logging_level=logging.WARNING,
    use_environment_variables=False,
):
    """Load the current configuration.

    An example of a valid line in a configuration file is this:

        data_objects.auto_close  True

    When this function is called without parameters, it reads all client settings from
    a configuration file (the path given by DEFAULT_CONFIG_PATH, since file = '' in such
    an invocation) and assigns the repr()-style Python value given into the dotted-string
    configuration entry given.

    The 'file' parameter, when set to a non-empty string, provides an override for
    the config-file path default.

    As with save(), 'root' refers to the starting location in the settings tree, with
    a value of None denoting the top tree node (ie the namespace containing *all* settings).
    There are as yet no imagined use-cases for an application developer to pass in an
    explicit 'root' override.

    'failure_modes' is an iterable containing desired exception types to be thrown if,
    for example, the configuration file is missing (NoConfigError) or contains an improperly
    formatted line (BadConfigError).

    'logging_level' governs the internally logged messages and can be used to e.g. quiet the
    call's logging output.
    """

    def _existing_config(path):
        if os.path.isfile(path):
            return open(path, "r")
        message = "Config file not available at %r" % (path,)
        logging.getLogger(__name__).log(logging_level, message)
        if NoConfigError in failure_modes:
            raise NoConfigError(message)
        return io.StringIO()

    _file = None
    try:
        if not file:
            from .. import get_settings_path

            file = get_settings_path()

        _file = _existing_config(file)

        if root is None:
            root = sys.modules[__name__]

        if verify_only:
            return

        for line_number, line in enumerate(_file.readlines()):
            line = line.strip()
            match = _key_value_pattern.match(line)
            if not match:
                if line != "":
                    # Log only the invalid lines that contain non-whitespace characters.
                    message = "Invalid configuration format at line %d: %r" % (
                        line_number + 1,
                        line,
                    )
                    logging.getLogger(__name__).log(logging_level, message)
                    if BadConfigError in failure_modes:
                        raise BadConfigError(message)
                continue
            _load_config_line(root, match.group("key"), match.group("value"))

        if use_environment_variables:
            _load_settings_from_environment(root)

    finally:
        if _file:
            _file.close()


default_config_dict = {}


def _load_settings_from_environment(root=None):
    if root is None:
        root = sys.modules[__name__]
    for key, variable in _calculate_overriding_environment_variables().items():
        value = os.environ.get(variable)
        if value is not None:
            _load_config_line(root, key, value)


def preserve_defaults():
    default_config_dict.update(
        (k, copy.deepcopy(v))
        for k, v in globals().items()
        if isinstance(v, iRODSConfiguration)
    )


def autoload(_file_to_load):
    if _file_to_load is None:
        _load_settings_from_environment()
    else:
        load(file=_file_to_load, use_environment_variables=True)


def new_default_config():
    module = types.ModuleType("_")
    module.__dict__.update(default_config_dict)
    return module


def overriding_environment_variables():
    uppercase_and_dot_split = lambda _: _.upper().split(".")
    return {
        _tuple.dotted: "__".join(
            ["PYTHON_IRODSCLIENT_CONFIG"] + uppercase_and_dot_split(_tuple.dotted)
        )
        for _tuple in _var_item_tuples_as_generator()
        if _tuple.is_config
    }


def _calculate_overriding_environment_variables(
    memo=overriding_environment_variables(),
):
    return memo
