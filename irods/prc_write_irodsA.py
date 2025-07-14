#!/usr/bin/env python3

import getopt
import textwrap
import sys
from typing import Callable, Dict

from irods.auth.pam_password import _get_pam_password_from_stdin as get_password
from irods.client_init import write_pam_irodsA_file, write_native_irodsA_file

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

    vector : Dict[str, Callable] = {"pam_password": write_pam_irodsA_file, "native": write_native_irodsA_file}
    opts, args = getopt.getopt(sys.argv[1:], "hi:", ["ttl=", "help"])
    optD = dict(opts)
    help_selected = {*optD} & {"-h", "--help"}
    if len(args) != 1 or help_selected:
        print(
            "{}\nUsage: {} [-i STREAM| -h | --help | --ttl HOURS] AUTH_SCHEME".format(
                extra_help, sys.argv[0]
            )
        )
        print("  Choices for AUTH_SCHEME are:")
        for x in vector:
            print("    {}".format(x))
        print(
            "  STREAM is the name of a file containing a password. Alternatively, a hyphen('-') is used to\n"
            "  indicate that the password may be read from stdin."
        )
        sys.exit(0 if help_selected else 1)
    scheme = args[0]
    if scheme in vector:
        options = {}
        inp_stream = optD.get("-i", None)
        if "--ttl" in optD:
            options["ttl"] = optD["--ttl"]
        if inp_stream is None or inp_stream == "-":
            pw = get_password(sys.stdin,
                              prompt=f"Enter current password for scheme {scheme!r}: ",)
        else:
            pw = get_password(open(inp_stream, "r", encoding='utf-8'),
                              prompt=f"Enter current password for scheme {scheme!r}: ",)
        vector[scheme](pw, **options)
    else:
        print("did not recognize authentication scheme argument", file=sys.stderr)
