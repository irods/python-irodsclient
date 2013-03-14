import logging
MAX_PASSWORD_LENGTH = 50

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
h = logging.StreamHandler()
f = logging.Formatter("%(asctime)s %(name)s-%(levelname)s [%(pathname)s %(lineno)d] %(message)s")
h.setFormatter(f)
logger.addHandler(h)
