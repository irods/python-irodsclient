class PamLoginException(Exception):
    pass


def login(conn, **opts):
    msg = (
        "In iRODS 4.3+, PAM logins use the new authentication plugin framework by default, which "
        "requires the authentication scheme be set to 'pam_password' rather than simply 'pam'.  "
        "Users may choose legacy authentication "
        "by setting legacy_auth.force_legacy_auth to True in the client configuration; however, be advised "
        "that the legacy code path will be removed in a future release of iRODS."
    )
    raise PamLoginException(msg)
