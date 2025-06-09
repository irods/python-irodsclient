import sys

minimum_compatible_python = (3, 6)

if sys.version_info < minimum_compatible_python:
    to_dotted_string = lambda version_tuple: ".".join(str(_) for _ in version_tuple)
    version_message = "This library is only supported on Python {} and above.".format(
        to_dotted_string(minimum_compatible_python)
    )
    raise RuntimeError(version_message)

from .version import __version__, version_as_tuple, version_as_string

import logging
import os


def env_filename_from_keyword_args(kwargs):
    try:
        env_file = kwargs.pop("irods_env_file")
    except KeyError:
        try:
            env_file = os.environ["IRODS_ENVIRONMENT_FILE"]
        except KeyError:
            env_file = os.path.expanduser("~/.irods/irods_environment.json")
    return env_file


def derived_auth_filename(env_filename):
    if not env_filename:
        return ""
    default_irods_authentication_file = os.path.expanduser("~/.irods/.irodsA")
    return os.environ.get(
        "IRODS_AUTHENTICATION_FILE", default_irods_authentication_file
    )


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
gHandler = None


def client_logging(flag=True, handler=None):
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
            if gHandler:
                logger.removeHandler(gHandler)
            if not handler:
                handler = logging.StreamHandler()
            gHandler = handler
            logger.addHandler(handler)
    else:
        if gHandler:
            logger.removeHandler(gHandler)
        gHandler = None
    return gHandler


# Magic Numbers
MAX_PASSWORD_LENGTH = 50
MAX_SQL_ATTR = 50
MAX_PATH_ALLOWED = 1024
MAX_NAME_LEN = MAX_PATH_ALLOWED + 64
LONG_NAME_LEN = 256
RESPONSE_LEN = 16
CHALLENGE_LEN = 64
MAX_SQL_ROWS = 256
DEFAULT_CONNECTION_TIMEOUT = 120
# https://stackoverflow.com/questions/45704243/value-of-c-pytime-t-in-python
MAXIMUM_CONNECTION_TIMEOUT = 9223372036

AUTH_SCHEME_KEY = "a_scheme"
AUTH_USER_KEY = "a_user"
AUTH_PWD_KEY = "a_pw"
AUTH_TTL_KEY = "a_ttl"

NATIVE_AUTH_SCHEME = "native"

GSI_AUTH_PLUGIN = "GSI"
GSI_AUTH_SCHEME = GSI_AUTH_PLUGIN.lower()
GSI_OID = "1.3.6.1.4.1.3536.1.1"  # taken from http://j.mp/2hDeczm

PAM_AUTH_PLUGIN = "PAM"
PAM_AUTH_SCHEME = PAM_AUTH_PLUGIN.lower()
PAM_AUTH_SCHEMES = (PAM_AUTH_SCHEME, "pam_password", "pam_interactive")

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.python_irodsclient")
settings_path_environment_variable = "PYTHON_IRODSCLIENT_CONFIGURATION_PATH"


def get_settings_path():
    env_var = os.environ.get(settings_path_environment_variable)
    return DEFAULT_CONFIG_PATH if not env_var else env_var


from . import client_configuration

client_configuration.preserve_defaults()

# If the settings path variable is not set in the environment, a value of None is passed,
# and thus no settings file is auto-loaded.
client_configuration.autoload(
    _file_to_load=os.environ.get(settings_path_environment_variable)
)
