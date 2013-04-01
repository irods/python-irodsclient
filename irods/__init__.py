import logging

# Magic Numbers
MAX_PASSWORD_LENGTH = 50
MAX_SQL_ATTR = 50
MAX_PATH_ALLOWED = 1024
MAX_NAME_LEN = MAX_PATH_ALLOWED + 64
RESPONSE_LEN = 16
CHALLENGE_LEN = 64

# File access modes
O_RDONLY = 0
O_WRONLY = 1
O_RDWR = 2

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
h = logging.StreamHandler()
f = logging.Formatter("%(asctime)s %(name)s-%(levelname)s [%(pathname)s %(lineno)d] %(message)s")
h.setFormatter(f)
logger.addHandler(h)

