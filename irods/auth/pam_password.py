def login(conn):
    conn._login_pam()


#   # in the future we might need cross-plugin calls:
#   native_login(conn)  # see below for import

# Pattern for when you need to import from sibling plugins:
from .native import login as native_login
