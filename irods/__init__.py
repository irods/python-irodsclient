from .version import __version__

import logging
import os

# This has no effect if basicConfig() was previously called.
logging.basicConfig()

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
gHandler = None

def client_logging(flag=True,handler=None):
    """
    Example of use:

    import irods
    # Enable / Disable general client logging
    irods.client_logging(True[,handler]) -> handler
    #    (handler is a StreamHandler to stderr by default)
    irods.client_logging(False)  # - disable irods client logging
    """
    global gHandler
    if flag:
        if handler is not None:
            if gHandler: logger.removeHandler(gHandler)
            if not handler: handler = logging.StreamHandler()
            gHandler = handler
            logger.addHandler(handler)
    else:
        if gHandler: logger.removeHandler(gHandler)
        gHandler = None
    return gHandler

# Magic Numbers
MAX_PASSWORD_LENGTH = 50
MAX_SQL_ATTR = 50
MAX_PATH_ALLOWED = 1024
MAX_NAME_LEN = MAX_PATH_ALLOWED + 64
RESPONSE_LEN = 16
CHALLENGE_LEN = 64
MAX_SQL_ROWS = 256
DEFAULT_CONNECTION_TIMEOUT = 120

AUTH_SCHEME_KEY = 'a_scheme'
AUTH_USER_KEY = 'a_user'
AUTH_PWD_KEY = 'a_pw'
AUTH_TTL_KEY = 'a_ttl'

NATIVE_AUTH_SCHEME = 'native'

GSI_AUTH_PLUGIN = 'GSI'
GSI_AUTH_SCHEME = GSI_AUTH_PLUGIN.lower()
GSI_OID = "1.3.6.1.4.1.3536.1.1"  # taken from http://j.mp/2hDeczm

PAM_AUTH_PLUGIN = 'PAM'
PAM_AUTH_SCHEME = PAM_AUTH_PLUGIN.lower()

DEFAULT_CONFIG_PATH = os.path.expanduser('~/.python_irodsclient')
settings_path_environment_variable = 'PYTHON_IRODSCLIENT_CONFIGURATION_PATH'

def get_settings_path():
    env_var = os.environ.get(settings_path_environment_variable)
    return DEFAULT_CONFIG_PATH if not env_var else env_var

from . import client_configuration

client_configuration.preserve_defaults()

# If the settings path variable is not set in the environment, a value of None is passed,
# and thus no settings file is auto-loaded.
client_configuration.autoload(_file_to_load = os.environ.get(settings_path_environment_variable))
