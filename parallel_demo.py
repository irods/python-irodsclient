#!/usr/bin/env python2
from __future__ import print_function
import os
import ssl
import sys
import contextlib
import time

from irods.session import iRODSSession

@contextlib.contextmanager
def get_session():
    try:
        env_file = os.environ['IRODS_ENVIRONMENT_FILE']
    except KeyError:
        env_file = os.path.expanduser('~/.irods/irods_environment.json')
    ssl_context = ssl.create_default_context( purpose=ssl.Purpose.SERVER_AUTH,
                                              cafile=None, capath=None, cadata=None)
    ssl_settings = {'ssl_context': ssl_context}
    session = iRODSSession(irods_env_file=env_file, **ssl_settings)
    try:
        yield session
    finally:
        session.cleanup()

def main():

    Async = bool(os.environ.get("ASYNC",""))
    SkipWrite = bool(int(os.environ.get("SKIPWRITE","0")))
    N = int(os.environ.get("NTHR","1"))
    Resc =  os.environ.get("RESC","demoResc")
    useQueue =  bool(os.environ.get("QUEUE",""))

    M = (1 << 20)

    with get_session() as ses :

        if len(sys.argv[1:]) != 2:

            print("wrong # args",file = sys.stderr);exit()
        else:
            op,name = sys.argv[1:]
            if op.lower()[0] != 'g':
                if not SkipWrite:
                    with open(name,'wb') as f:
                        f.write(os.urandom(512*M if op.lower()[0] == 'p' else int(op)))
                print ('---',file=sys.stderr); sys.stderr.flush()
                T0 = time.time()
                r = ses.data_objects.parallel_put(name,
                                                  '/tempZone/home/rods/{}'.format(name),
                                                  async_ = Async,
                                                  num_threads=N,
                                                  target_resource_name = Resc,
                                                  progressQueue = useQueue
                                                 )
            else:
                T0 = time.time()
                r = ses.data_objects.parallel_get('/tempZone/home/rods/{}'.format(name),
                                                  name+'.get',
                                                  async_=Async,
                                                  num_threads=N,
                                                  target_resource_name = Resc,
                                                  progressQueue = useQueue
                                                 )
            if type(r) is bool:
                print ('transfer {}successful'.format('' if r else 'un'))
            else:
                print ('call returned, awaiting done condition')
                if r.wait_until_transfer_done (progressBar = useQueue): print('\n','done')
                else: print('\n','done, but failed')
            print ('transfer timed at', time.time() - T0, 'sec', file=sys.stderr)

if __name__ == '__main__':
    main()
#
## -- Demo progress bar
# bash -c 'ASYNC=1 SKIPWRITE=0 NTHR=3 RESC=demoResc QUEUE=1 python-irodsclient/parallel_demo.py $((2560*1024**2)) puttest'
# bash -c 'ASYNC=1 SKIPWRITE=1 NTHR=3 RESC=demoResc QUEUE=1 python-irodsclient/parallel_demo.py GET puttest'
#
## -- To verify
# diff puttest puttest.get

