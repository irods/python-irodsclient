from __future__ import print_function
import ast
import copy
import io
import logging
import os
import re
import sys
import types

# Duplicate here for convenience
from .. import DEFAULT_CONFIG_PATH

logger = logging.Logger(__name__)

class iRODSConfiguration(object):
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
    return lambda:getattr(globals()[category], setting)

# #############################################################################
#
# Classes for building client configuration categories
# (irods.client_configuration.data_objects is one such category):

class DataObjects(iRODSConfiguration):
    __slots__ = ('auto_close',)

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

def _var_items(root):
    if isinstance(root,types.ModuleType):
        return [(i,v) for i,v in vars(root).items()
                if isinstance(v,iRODSConfiguration)]
    if isinstance(root,iRODSConfiguration):
        return [(i, getattr(root,i)) for i in root.__slots__]
    return []

def save(root = None, string='', file = ''):
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
        if isinstance(file,str):
            _file = open(file,'w')
            auto_close_settings = True
        else:
            _file = file # assume file-like object if not a string
        if root is None:
            root = sys.modules[__name__]
        for k,v in _var_items(root):
            dotted_string = string + ("." if string else "") + k
            if isinstance(v,iRODSConfiguration):
                save(root = v, string = dotted_string, file = _file)
            else:
                print(dotted_string, repr(v), sep='\t\t', file = _file)
        return file
    finally:
        if _file and auto_close_settings:
            _file.close()

def _load_config_line(root, setting, value):
    arr = [_.strip() for _ in setting.split('.')]
    # Compute the object referred to by the dotted name.
    attr = ''
    for i in filter(None,arr):
        if attr:
            root = getattr(root,attr)
        attr = i
    # Assign into the current setting of the dotted name (effectively <root>.<attr>)
    # using the loaded value.
    if attr:
        return setattr(root, attr, ast.literal_eval(value))
    error_message = 'Bad setting: root = {root!r}, setting = {setting!r}, value = {value!r}'.format(**locals())
    raise RuntimeError (error_message)

# The following regular expression is used to match a configuration file line of the form:
# ---------------------------------------------------------------
#         <optional whitespace>
#  key:   <dotted-name specification>
#         <whitespace of length 1 or more>
#  value: <A Python value which can be given to ast.literal_eval(); e.g. 5, True, or 'some_string'>
#         <optional whitespace>

_key_value_pattern = re.compile(r'\s*(?P<key>\w+(\.\w+)+)\s+(?P<value>\S.*?)\s*$')

class _ConfigLoadError:
    """
    Exceptions that subclass this type can be thrown by the load() function if
    their classes are listed in the failure_modes parameter of that function.
    """

class NoConfigError(Exception, _ConfigLoadError): pass
class BadConfigError(Exception, _ConfigLoadError): pass

def load(root = None, file = '', failure_modes = (), logging_level = logging.WARNING):
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
            return open(path,'r')
        message = 'Config file not available at %r' % (path,)
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

        for line_number, line in enumerate(_file.readlines()):
            line = line.strip()
            match = _key_value_pattern.match(line)
            if not match:
                if line != '':
                    # Log only the invalid lines that contain non-whitespace characters.
                    message = 'Invalid configuration format at line %d: %r' % (line_number+1, line)
                    logging.getLogger(__name__).log(logging_level, message)
                    if BadConfigError in failure_modes:
                        raise BadConfigError(message)
                continue
            _load_config_line(root, match.group('key'), match.group('value'))
    finally:
        if _file:
            _file.close()

default_config_dict = {}

def preserve_defaults():
    default_config_dict.update((k,copy.deepcopy(v)) for k,v in globals().items() if isinstance(v,iRODSConfiguration))

def autoload(_file_to_load):
    if _file_to_load is not None:
        load(file = _file_to_load)

def new_default_config():
    module = types.ModuleType('_')
    module.__dict__.update(default_config_dict)
    return module
