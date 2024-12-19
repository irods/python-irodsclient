from getpass import getpass
from irods.password_obfuscation import encode
import json
import os
import sys
from os import chmod
from os.path import expanduser, exists, join
from getopt import getopt


home_env_path = expanduser("~/.irods")
env_file_path = join(home_env_path, "irods_environment.json")
auth_file_path = join(home_env_path, ".irodsA")


def do_iinit(host, port, user, zone, password):
    if not exists(home_env_path):
        os.makedirs(home_env_path)
    else:
        raise RuntimeError("~/.irods already exists")

    with open(env_file_path, "w") as env_file:
        json.dump(
            {
                "irods_host": host,
                "irods_port": int(port),
                "irods_user_name": user,
                "irods_zone_name": zone,
            },
            env_file,
            indent=4,
        )
    with open(auth_file_path, "w") as auth_file:
        auth_file.write(encode(password))
    chmod(auth_file_path, 0o600)


def get_kv_pairs_from_cmdline(*args):
    arglist = list(args)
    while arglist:
        k = arglist.pop(0)
        v = arglist.pop(0)
        yield k, v


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    dct = {k: v for k, v in get_kv_pairs_from_cmdline(*args)}
    do_iinit(**dct)
