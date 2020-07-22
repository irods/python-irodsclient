#!/usr/bin/env python

from __future__ import print_function
import os
import sys
import socket
import posix
import shutil
from subprocess import (Popen, PIPE)

IRODS_SSL_DIR = '/etc/irods/ssl'

def create_ssl_dir():
    save_cwd = os.getcwd()
    silent_run =  { 'shell': True, 'stderr' : PIPE, 'stdout' : PIPE }
    try:
        if not (os.path.exists(IRODS_SSL_DIR)):
            os.mkdir(IRODS_SSL_DIR)
        os.chdir(IRODS_SSL_DIR)
        Popen("openssl genrsa -out irods.key 2048",**silent_run).communicate()
        with open("/dev/null","wb") as dev_null:
            p = Popen("openssl req -new -x509 -key irods.key -out irods.crt -days 365 <<EOF{_sep_}"
                      "US{_sep_}North Carolina{_sep_}Chapel Hill{_sep_}UNC{_sep_}RENCI{_sep_}"
                      "{host}{_sep_}anon@mail.com{_sep_}EOF\n""".format(
                host = socket.gethostname(), _sep_="\n"),shell=True, stdout=dev_null, stderr=dev_null)
            p.wait()
            if 0 == p.returncode:
                Popen('openssl dhparam -2 -out dhparams.pem',**silent_run).communicate()
        return os.listdir(".")
    finally:
        os.chdir(save_cwd)

def test(opts,args=()):
    if args: print ('warning: non-option args are ignored',file=sys.stderr)
    affirm = 'n' if os.path.exists(IRODS_SSL_DIR) else 'y'
    if not [v for k,v in opts if k == '-f'] and affirm == 'n' and posix.isatty(sys.stdin.fileno()):
        try:
            input_ = raw_input
        except NameError:
            input_ = input
        affirm = input_("This will overwrite directory '{}'. Proceed(Y/N)? ".format(IRODS_SSL_DIR))
    if affirm[:1].lower() == 'y':
        shutil.rmtree(IRODS_SSL_DIR,ignore_errors=True)
        print("Generating new '{}'. This may take a while.".format(IRODS_SSL_DIR), file=sys.stderr)
        ssl_dir_files = create_ssl_dir()
        print('ssl_dir_files=', ssl_dir_files)
    
if __name__ == '__main__':
    import getopt
    test(*getopt.getopt(sys.argv[1:],'f')) # f = force
