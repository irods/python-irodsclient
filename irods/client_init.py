from irods import (env_filename_from_keyword_args, derived_auth_filename)
import irods.client_configuration as cfg
import irods.password_obfuscation as obf
import irods.helpers as h
import getpass
import os
import sys

def write_native_credentials_to_secrets_file(password, **kw):
    env_file = env_filename_from_keyword_args(kw)
    auth_file = derived_auth_filename(env_file)
    old_mask = None
    try:
        old_mask = os.umask(0o77)
        open(auth_file,'w').write(obf.encode(password))
    finally:
        if old_mask is not None:
            os.umask(old_mask)
            
    return True

def write_pam_credentials_to_secrets_file( password ,**kw):
    s = h.make_session()
    s.pool.account.password = password
    with cfg.loadlines( [dict(setting='legacy_auth.pam.password_for_auto_renew',value=None),
                         dict(setting='legacy_auth.pam.store_password_to_environment',value=False)] ):
        to_encode = s.pam_pw_negotiated
    if to_encode:
        open(s.pool.account.derived_auth_file,'w').write(obf.encode(to_encode[0]))
        return True
    return False

if __name__ == '__main__':
    vector = {
        'pam_password': write_pam_credentials_to_secrets_file,
        'native': write_native_credentials_to_secrets_file
    }

    if sys.argv[1] in vector:
        vector[sys.argv[1]](getpass.getpass(prompt=f'{sys.argv[1]} password: '))
    else:
        print('did not recognize authentication scheme argument',file = sys.stderr)
