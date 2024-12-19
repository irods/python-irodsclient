#!/usr/bin/env python

import numbers
import os
import posix
import socket
import shutil
from subprocess import Popen, PIPE
import sys

IRODS_SSL_DIR = "/etc/irods/ssl"
SERVER_CERT_HOSTNAME = None
ext = ""
keep_old = False


def create_server_cert(
    process_output=sys.stdout, irods_key_path="irods.key", hostname=SERVER_CERT_HOSTNAME
):
    p = Popen(
        "openssl req -new -x509 -key '{irods_key_path}' -out irods.crt{ext} -days 365 <<EOF{_sep_}"
        "US{_sep_}North Carolina{_sep_}Chapel Hill{_sep_}UNC{_sep_}RENCI{_sep_}"
        "{host}{_sep_}anon@mail.com{_sep_}EOF\n"
        "".format(
            ext=ext,
            host=(hostname if hostname else socket.gethostname()),
            _sep_="\n",
            **locals()
        ),
        shell=True,
        stdout=process_output,
        stderr=process_output,
    )
    p.wait()
    return p.returncode


def create_ssl_dir(
    irods_key_path="irods.key", ssl_dir="", use_strong_primes_for_dh_generation=True
):
    ssl_dir = ssl_dir or IRODS_SSL_DIR
    save_cwd = os.getcwd()
    silent_run = {"shell": True, "stderr": PIPE, "stdout": PIPE}
    try:
        if not (os.path.exists(ssl_dir)):
            os.mkdir(ssl_dir)
        os.chdir(ssl_dir)
        if not keep_old:
            Popen(
                "openssl genrsa -out '{irods_key_path}' 2048 && chmod 600 '{irods_key_path}'".format(
                    **locals()
                ),
                **silent_run
            ).communicate()
        with open("/dev/null", "wb") as dev_null:
            if 0 == create_server_cert(
                process_output=dev_null, irods_key_path=irods_key_path
            ):
                if not keep_old:
                    # https://www.openssl.org/docs/man1.0.2/man1/dhparam.html#:~:text=DH%20parameter%20generation%20with%20the,that%20may%20be%20possible%20otherwise.
                    if use_strong_primes_for_dh_generation:
                        dhparam_generation_command = (
                            "openssl dhparam -2 -out dhparams.pem"
                        )
                    else:
                        dhparam_generation_command = (
                            "openssl dhparam -dsaparam -out dhparams.pem 4096"
                        )
                    print("cmd=", dhparam_generation_command)
                    Popen(dhparam_generation_command, **silent_run).communicate()
        return os.listdir(".")
    finally:
        os.chdir(save_cwd)


def test(options, args=()):
    if args:
        print("warning: non-option args are ignored", file=sys.stderr)
    force = "-f" in options
    affirm = "n" if (os.path.exists(IRODS_SSL_DIR) and not force) else "y"
    if affirm == "n" and posix.isatty(sys.stdin.fileno()):
        try:
            input_ = raw_input
        except NameError:
            input_ = input
        affirm = input_(
            "This will overwrite directory '{}'. Proceed(Y/N)? ".format(IRODS_SSL_DIR)
        )
    if affirm[:1].lower() == "y":
        if not keep_old:
            shutil.rmtree(IRODS_SSL_DIR, ignore_errors=True)
        dh_strong_primes = "-q" not in options
        wait_warning = " This may take a while." if dh_strong_primes else ""
        print(
            "Generating new '{}'.{}".format(IRODS_SSL_DIR, wait_warning),
            file=sys.stderr,
        )
        ssl_dir_files = create_ssl_dir(
            use_strong_primes_for_dh_generation=dh_strong_primes
        )
        print("ssl_dir_files=", ssl_dir_files, file=sys.stderr)


def usage(exit_code=None):

    print(
        """Usage: {sys.argv[0]} [-f] [-h <hostname>] [-k] [-q] [-x <extension>] 
    -f      Force replacement of the existing SSL directory (/etc/irods/ssl) with a new one, containing newly generated files.
    -h      In the generated certificate, use the given hostname rather than the value returned from socket.gethostname()
    -k      (Keep old secrets files.) Do not generate new key file or dhparams.pem file.
    -q      For testing; do a quick generation of a dhparams.pem file rather than waiting on system entropy to make it more secure.
    -x      Optional extra extension for appending to end of the filename for the generated certificate.
    --help  Print this help.

    Any invalid option prints this help.
    """.format(
            **globals()
        ),
        file=sys.stderr,
    )
    if isinstance(exit_code, numbers.Integral):
        exit(exit_code)


if __name__ == "__main__":
    import getopt

    try:
        opt, arg_list = getopt.getopt(sys.argv[1:], "x:fh:kq", ["help"])
    except getopt.GetoptError:
        usage(exit_code=1)

    opt_lookup = dict(opt)

    if "--help" in opt_lookup:
        usage(exit_code=0)

    ext = opt_lookup.get("-x", "")
    if ext:
        ext = "." + ext.lstrip(".")
    keep_old = opt_lookup.get("-k") is not None
    SERVER_CERT_HOSTNAME = opt_lookup.get("-h")
    test(opt_lookup, arg_list)
