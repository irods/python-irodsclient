import contextlib
import getpass
import os
import sys

from irods import (env_filename_from_keyword_args, derived_auth_filename)
import irods.client_configuration as cfg
import irods.password_obfuscation as obf
import irods.helpers as h

@contextlib.contextmanager
def _open_file_for_protected_contents(file_path,*arg,**kw):
    f = old_mask = None
    try:
        old_mask = os.umask(0o77)
        f = open(file_path,*arg,**kw)
        yield f
    finally:
        if f is not None:
            f.close()
        if old_mask is not None:
            os.umask(old_mask)

def write_native_credentials_to_secrets_file(password, overwrite = True, **kw):
    """Write the credentials to an .irodsA file that will enable logging in with native authentication
       using the given cleartext password.

       If overwrite is False, an already existing .irodsA will not be overwritten.

       Returns: True if credentials were written to the .irodsA file.
    """
    env_file = env_filename_from_keyword_args(kw)
    auth_file = derived_auth_filename(env_file)
    old_mask = os.umask(0o77)
    if overwrite or not os.path.exists(auth_file):
        with _open_file_for_protected_contents(auth_file,'w',**kw) as irodsA:
            irodsA.write(obf.encode(password))
        return True
    return False

def write_pam_credentials_to_secrets_file(password, overwrite = True, **kw):
    """Write the credentials to an .irodsA file that will enable logging in with PAM authentication
       using the given cleartext password.

       If overwrite is False, an already existing .irodsA will not be overwritten.

       Returns: True if credentials were written to the .irodsA file.
    """
    s = h.make_session()
    s.pool.account.password = password
    with cfg.loadlines( [dict(setting='legacy_auth.pam.password_for_auto_renew',value=None),
                         dict(setting='legacy_auth.pam.store_password_to_environment',value=False)] ):
        to_encode = s.pam_pw_negotiated
    auth_file_path = s.pool.account.derived_auth_file
    if overwrite or not os.path.exists(auth_file):
        if to_encode:
            with _open_file_for_protected_contents(auth_file,'w',**kw) as irodsA:
                irodsA.write(obf.encode(to_encode[0]))
            return True
    return False

if __name__ == '__main__':
    vector = {
        'pam_password': write_pam_credentials_to_secrets_file,
        'native': write_native_credentials_to_secrets_file
    }

    if len(sys.argv) != 2:
        print('Usage: {} AUTH_SCHEME'.format(sys.argv[0]))
        print('  AUTH_SCHEME:')
        for x in vector:
            print('    {}'.format(x))
        sys.exit(1)
    elif sys.argv[1] in vector:
        vector[sys.argv[1]](getpass.getpass(prompt=f'{sys.argv[1]} password: '))
    else:
        print('did not recognize authentication scheme argument',file = sys.stderr)
