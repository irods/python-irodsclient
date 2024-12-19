class PamLoginException(Exception):
    pass


def login(conn):
    if conn.server_version >= (4, 3):
        raise PamLoginException(
            'PAM logins in iRODS 4.3+ require a scheme of "pam_password"'
        )
    conn._login_pam()


# Pattern for when you need to import from sibling plugins:
from .native import login as native_login
