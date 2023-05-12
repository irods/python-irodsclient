import gc
import sys
from irods.session import _weakly_reference, SessionThread, iRODSSession
from irods.test import helpers as helpers

def f(ses):
        c = helpers.home_collection(ses)
        print (ses.collections.get(c))

class MyThread(SessionThread):

    def __init__(self, sess = None, func = None, **kwargs):
        super(MyThread,self).__init__(**kwargs)
        self.sess = sess
        if sess:
            _weakly_reference(sess, parent_thread = self)
        self.func = func

    def run(self):
        self.func(self.sess)

class my_iRODSSession(iRODSSession):
    def cleanup(self,*arg,**kwarg):
        print("cleanup called on {self}".format(**locals()))
        return super(my_iRODSSession,self).cleanup(*arg,**kwarg)

if __name__ == '__main__':
    import irods.session

    def _main_thread_sessions():
        return () if irods.session._sessions is None \
          else list(irods.session._sessions.keys())

    s = my_iRODSSession( host='localhost',
                         port=1247,
                         user='rods',
                         password='rods',
                         zone='tempZone'
                       )
    t = MyThread(
                    sess = s,
                    func = f,
                    )
    t.start()
    t.join()
    del t
    del s
    print("->thread successfully joined.")
    gc.collect()
    print("-> garbage collected.")
    print("atexit will be calling cleanup on:", _main_thread_sessions())
