import logging

# iRODS settings
IRODS_VERSION = {'major': 4, 'minor': 2, 'patchlevel': 0, 'api': 'd'}

# Magic Numbers
MAX_PASSWORD_LENGTH = 50
MAX_SQL_ATTR = 50
MAX_PATH_ALLOWED = 1024
MAX_NAME_LEN = MAX_PATH_ALLOWED + 64
RESPONSE_LEN = 16
CHALLENGE_LEN = 64
MAX_SQL_ROWS = 256

# Other variables
AUTH_SCHEME_KEY = 'a_scheme'
GSI_AUTH_PLUGIN = 'GSI'
GSI_AUTH_SCHEME = GSI_AUTH_PLUGIN.lower()
GSI_OID = "1.3.6.1.4.1.3536.1.1"  # taken from http://j.mp/2hDeczm

# logger = logging.getLogger()
# logger.setLevel(logging.ERROR)
# h = logging.StreamHandler()
# f = logging.Formatter(
#     "%(asctime)s %(name)s-%(levelname)s [%(pathname)s %(lineno)d] %(message)s")
# h.setFormatter(f)
# logger.addHandler(h)