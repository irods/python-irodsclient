#!/usr/bin/env python3

import contextlib
import getpass
import os
import sys
import textwrap

from irods import env_filename_from_keyword_args, derived_auth_filename
import irods.client_configuration as cfg
import irods.password_obfuscation as obf
import irods.helpers as h


@contextlib.contextmanager
def _open_file_for_protected_contents(file_path, *arg, **kw):
    f = old_mask = None
    try:
        old_mask = os.umask(0o77)
        f = open(file_path, *arg, **kw)
        yield f
    finally:
        if old_mask is not None:
            os.umask(old_mask)
        if f is not None:
            f.close()


class irodsA_already_exists(Exception):
    pass


def _write_encoded_auth_value(auth_file, encode_input, overwrite):
    if not auth_file:
        raise RuntimeError(f"Path to irodsA ({auth_file}) is null.")
    if not overwrite and os.path.exists(auth_file):
        raise irodsA_already_exists(
            f"Overwriting not enabled and {auth_file} already exists."
        )
    with _open_file_for_protected_contents(auth_file, "w") as irodsA:
        irodsA.write(obf.encode(encode_input))


def write_native_credentials_to_secrets_file(password, overwrite=True, **kw):
    """Write the credentials to an .irodsA file that will enable logging in with native authentication
    using the given cleartext password.

    If overwrite is False, irodsA_already_exists will be raised if an .irodsA is found at the
    expected path.
    """
    env_file = env_filename_from_keyword_args(kw)
    auth_file = derived_auth_filename(env_file)
    _write_encoded_auth_value(auth_file, password, overwrite)

## TODO fully re-implement the free function to write a PAM .irodsA file to use new auth-framework machinery:
## (Here's a start:)
# def write_pam_irodsA_file(password, overwrite=True, **kw):
#     import irods.auth.pam_password
#     ses = h.make_session()
#     pam_opt[ irods.auth.FORCE_PASSWORD_PROMPT ] = io.StringIO(password)
#     pam_opt[ irods.auth.CLIENT_GET_REQUEST_RESULT ] = L = []


def write_pam_credentials_to_secrets_file(password, overwrite=True, **kw):
    """Write the credentials to an .irodsA file that will enable logging in with PAM authentication
    using the given cleartext password.

    If overwrite is False, irodsA_already_exists will be raised if an .irodsA is found at the
    expected path.
    """
    s = h.make_session()
    s.pool.account.password = password
    to_encode = []
    with cfg.loadlines(
        [
            dict(setting="legacy_auth.pam.password_for_auto_renew", value=None),
            dict(setting="legacy_auth.pam.store_password_to_environment", value=False),
        ]
    ):
        to_encode = s.pam_pw_negotiated
    if not to_encode:
        raise RuntimeError(f"Password token was not passed from server.")
    auth_file = s.pool.account.derived_auth_file
    _write_encoded_auth_value(auth_file, to_encode[0], overwrite)


if __name__ == "__main__":
    extra_help = textwrap.dedent(
        """
    This Python module also functions as a script to produce a "secrets" (i.e. encoded password) file.
    Similar to iinit in this capacity, if the environment - and where applicable, the PAM
    configuration for both system and user - is already set up in every other regard, this program
    will generate the secrets file with appropriate permissions and in the normal location, usually:

       ~/.irods/.irodsA

    The user will be interactively prompted to enter their cleartext password.
    """
    )

    vector = {
        "pam_password": write_pam_credentials_to_secrets_file,
        "native": write_native_credentials_to_secrets_file,
    }

    if len(sys.argv) != 2:
        print("{}\nUsage: {} AUTH_SCHEME".format(extra_help, sys.argv[0]))
        print("  AUTH_SCHEME:")
        for x in vector:
            print("    {}".format(x))
        sys.exit(1)
    elif sys.argv[1] in vector:
        vector[sys.argv[1]](getpass.getpass(prompt=f"{sys.argv[1]} password: "))
    else:
        print("did not recognize authentication scheme argument", file=sys.stderr)
