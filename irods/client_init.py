import irods.client_configuration as cfg
import irods.password_obfuscation as obf
import irods.helpers as h
import getpass
import sys

def write_credentials_with_native_password( password ):
    s = h.make_session()
    assert(not s.auth_file)
    open(s.pool.account.derived_auth_file,'w').write(obf.encode(password))
    return True

def write_credentials_with_pam_password( password ):
    s = h.make_session()
    assert(not s.auth_file)
    s.pool.account.password = password
    with cfg.loadlines( [dict(setting='legacy_auth.pam.password_for_auto_renew',value='')] ):
        to_encode = s.pam_pw_negotiated
    if to_encode:
        open(s.pool.account.derived_auth_file,'w').write(obf.encode(to_encode[0]))
        return True
    return False

if __name__ == '__main__':
    vector = {
        'pam': write_credentials_with_pam_password,
        'native': write_credentials_with_native_password,
    }

    if sys.argv[1] in vector:
        vector[sys.argv[1]](getpass.getpass(prompt=f'{sys.argv[1]} password: '))
    else:
        print('did not recognize authentication scheme argument',file = sys.stderr)
