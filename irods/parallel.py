#!/usr/bin/env python
from __future__ import print_function

import os
import ssl
import time
import sys
import logging
import contextlib
import concurrent.futures
import threading
import multiprocessing
import six

from irods.data_object import iRODSDataObject
from irods.exception import DataObjectDoesNotExist
import irods.keywords as kw
from six.moves.queue import Queue,Full,Empty


logger = logging.getLogger( __name__ )
_nullh  = logging.NullHandler()
logger.addHandler( _nullh )


MINIMUM_SERVER_VERSION = (4,2,9)


class deferred_call(object):

    """
    A callable object that stores a function to be called later, along
    with its parameters.
    """

    def __init__(self, function, args, keywords):
        """Initialize the object with a function and its call parameters."""
        self.function = function
        self.args = args
        self.keywords = keywords

    def __setitem__(self, key, val):
        """Allow changing a keyword option for the deferred function call."""
        self.keywords[key] = val

    def __call__(self):
        """Call the stored function, using the arguments and keywords also stored
        in the instance."""
        return self.function(*self.args, **self.keywords)


try:
    from threading import Barrier   # Use 'Barrier' class if included (as in Python >= 3.2) ...
except ImportError:                 # ... but otherwise, use this ad hoc:
    # Based on https://stackoverflow.com/questions/26622745/implementing-barrier-in-python2-7 :
    class Barrier(object):
        def __init__(self, n):
            """Initialize a Barrier to wait on n threads."""
            self.n = n
            self.count = 0
            self.mutex = threading.Semaphore(1)
            self.barrier = threading.Semaphore(0)
        def wait(self):
            """Per-thread wait function.

            As in Python3.2 threading, returns 0 <= wait_serial_int < n
            """
            self.mutex.acquire()
            self.count += 1
            count = self.count
            self.mutex.release()
            if count == self.n: self.barrier.release()
            self.barrier.acquire()
            self.barrier.release()
            return count - 1

@contextlib.contextmanager
def enableLogging(handlerType,args,level_ = logging.INFO):
    """Context manager for temporarily enabling a logger. For debug or test.

    Usage Example -
    with irods.parallel.enableLogging(logging.FileHandler,('/tmp/logfile.txt',)):
        # parallel put/get code here
    """
    h = None
    saveLevel = logger.level
    try:
        logger.setLevel(level_)
        h = handlerType(*args)
        h.setLevel( level_ )
        logger.addHandler(h)
        yield
    finally:
        logger.setLevel(saveLevel)
        if h in logger.handlers:
            logger.removeHandler(h)


RECOMMENDED_NUM_THREADS_PER_TRANSFER = 3

verboseConnection = False

class BadCallbackTarget(TypeError): pass

class AsyncNotify (object):

    """A type returned when the PUT or GET operation passed includes NONBLOCKING.
       If enabled, the callback function (or callable object) will be triggered
       when all parts of the parallel transfer are complete.  It should accept
       exactly one argument, the irods.parallel.AsyncNotify instance that
       is calling it.
    """

    def set_transfer_done_callback( self, callback ):
        if callback is not None:
            if not callable(callback):
                raise BadCallbackTarget( '"callback" must be a callable accepting at least 1 argument' )
        self.done_callback = callback

    def __init__(self, futuresList, callback = None, progress_Queue = None, total = None, keep_ = ()):
        """AsyncNotify initialization (used internally to the io.parallel library).
           The casual user will only be concerned with the callback parameter, called when all threads
           of the parallel PUT or GET have been terminated and the data object closed.
        """
        self._futures = set(futuresList)
        self._futures_done = dict()
        self.keep = dict(keep_)
        self._lock = threading.Lock()
        self.set_transfer_done_callback (callback)
        self.__done = False
        if self._futures:
            for future in self._futures: future.add_done_callback( self )
        else:
            self.__invoke_done_callback()

        self.progress = [0, 0]
        if (progress_Queue) and (total is not None):
            self.progress[1] = total
            def _progress(Q,this):  # - thread to update progress indicator
                while this.progress[0] < this.progress[1]:
                    i = None
                    try:
                        i = Q.get(timeout=0.1)
                    except Empty:
                        pass
                    if i is not None:
                        if isinstance(i,six.integer_types) and i >= 0: this.progress[0] += i
                        else: break
            self._progress_fn = _progress
            self._progress_thread = threading.Thread( target = self._progress_fn, args = (progress_Queue, self))
            self._progress_thread.start()

    @staticmethod
    def asciiBar( lst, memo = [1] ):
        memo[0] += 1
        spinner = "|/-\\"[memo[0]%4]
        percent = "%5.1f%%"%(lst[0]*100.0/lst[1])
        mbytes = "%9.1f MB / %9.1f MB"%(lst[0]/1e6,lst[1]/1e6)
        if lst[1] != 0:
            s = "  {spinner} {percent} [ {mbytes} ] "
        else:
            s = "  {spinner} "
        return s.format(**locals())

    def wait_until_transfer_done (self, timeout=float('inf'), progressBar = False):
        carriageReturn = '\r'
        begin = t = time.time()
        end = begin + timeout
        while not self.__done:
            time.sleep(min(0.1, max(0.0, end - t)))
            t = time.time()
            if t >= end: break
            if progressBar:
                print ('  ' + self.asciiBar( self.progress ) + carriageReturn, end='', file=sys.stderr)
                sys.stderr.flush()
        return self.__done

    def __call__(self,future): # Our instance is called by each future (individual file part) when done.
                               # When all futures are done, we invoke the configured callback.
        with self._lock:
            self._futures_done[future] = future.result()
            if len(self._futures) == len(self._futures_done): self.__invoke_done_callback()

    def __invoke_done_callback(self):
        try:
            if callable(self.done_callback): self.done_callback(self)
        finally:
            self.keep.pop('mgr',None)
            self.__done = True
        self.set_transfer_done_callback(None)

    @property
    def futures(self): return list(self._futures)

    @property
    def futures_done(self): return dict(self._futures_done)


class Oper(object):

    """A custom enum-type class with utility methods.

    It makes some logic clearer, including succinct calculation of file and data
    object open() modes based on whether the operation is a PUT or GET and whether
    we are doing the "initial" open of the file or object.
    """

    GET = 0
    PUT = 1
    NONBLOCKING = 2

    def __int__(self):
        """Return the stored flags as an integer bitmask. """
        return self._opr

    def __init__(self, rhs):
        """Initialize with a bit mask of flags ie. whether Operation PUT or GET, 
        and whether NONBLOCKING."""
        self._opr = int(rhs)

    def isPut(self): return 0 != (self._opr & self.PUT)
    def isGet(self): return not self.isPut()
    def isNonBlocking(self): return 0 != (self._opr & self.NONBLOCKING)

    def data_object_mode(self, initial_open = False):
        if self.isPut():
            return 'w' if initial_open else 'a'
        else:
            return 'r'

    def disk_file_mode(self, initial_open = False, binary = True):
        if self.isPut():
            mode = 'r'
        else:
            mode = 'w' if initial_open else 'r+'
        return ((mode + 'b') if binary else mode)


def _io_send_bytes_progress (queueObject, item):
    try:
        queueObject.put(item)
        return True
    except Full:
        return False

COPY_BUF_SIZE = (1024 ** 2) * 4

def _copy_part( src, dst, length, queueObject, debug_info, mgr):
    """
    The work-horse for performing the copy between file and data object.

    It also helps determine whether there has been a large enough increment of
    bytes to inform the progress bar of a need to update.
    """
    bytecount = 0
    accum = 0
    while True and bytecount < length:
        buf = src.read(min(COPY_BUF_SIZE, length - bytecount))
        buf_len = len(buf)
        if 0 == buf_len: break
        dst.write(buf)
        bytecount += buf_len
        accum += buf_len
        if queueObject and accum and _io_send_bytes_progress(queueObject,accum): accum = 0
        if verboseConnection:
            print ("("+debug_info+")",end='',file=sys.stderr)
            sys.stderr.flush()

    # In a put or get, exactly one of (src,dst) is a file. Find which and close that one first.
    (file_,obj_) = (src,dst) if dst in mgr else (dst,src)
    file_.close()
    mgr.remove_io( obj_ ) # 1. closes obj if it is not the mgr's initial descriptor
                          # 2. blocks at barrier until all transfer threads are done copying
                          # 3. closes with finalize if obj is mgr's initial descriptor
    return bytecount


class _Multipart_close_manager:
    """An object used to ensure that the initial transfer thread is also the last one to
    call the close method on its `Io' object.  The caller is responsible for setting up the
    conditions that the initial thread's close() is the one performing the catalog update.

    All non-initial transfer threads just call close() as soon as they are done transferring
    the byte range for which they are responsible, whereas we block the initial thread
    using a threading Barrier until we know all other threads have called close().

    """
    def __init__(self, initial_io_, exit_barrier_):
        self.exit_barrier = exit_barrier_
        self.initial_io = initial_io_
        self.__lock = threading.Lock()
        self.aux = []

    def __contains__(self,Io):
        with self.__lock:
            return Io is self.initial_io or \
                   Io in self.aux

    # `add_io' - add an i/o object to be managed
    # note: `remove_io' should only be called for managed i/o objects

    def add_io(self,Io):
        with self.__lock:
            if Io is not self.initial_io:
                self.aux.append(Io)

    # `remove_io' is for closing a channel of parallel i/o and allowing the
    # data object to flush write operations (if any) in a timely fashion.  It also
    # synchronizes all of the parallel threads just before exit, so that we know
    # exactly when to perform a finalizing close on the data object

    def remove_io(self,Io):
        is_initial = True
        with self.__lock:
            if Io is not self.initial_io:
                Io.close()
                self.aux.remove(Io)
                is_initial = False
        self.exit_barrier.wait()
        if is_initial: self.finalize()

    def finalize(self):
        self.initial_io.close()


def _io_part (objHandle, range_, file_, opr_, mgr_, thread_debug_id = '', queueObject = None ):
    """
    Runs in a separate thread to manage the transfer of a range of bytes within the data object.

    The particular range is defined by the end of the range_ parameter, which should be of type
    (Py2) xrange or (Py3) range.
    """
    if 0 == len(range_): return 0
    Operation = Oper(opr_)
    (offset,length) = (range_[0], len(range_))
    objHandle.seek(offset)
    file_.seek(offset)
    if thread_debug_id == '':  # for more succinct thread identifiers while debugging.
        thread_debug_id = str(threading.currentThread().ident)
    return ( _copy_part (file_, objHandle, length, queueObject, thread_debug_id, mgr_) if Operation.isPut()
        else _copy_part (objHandle, file_, length, queueObject, thread_debug_id, mgr_) )


def _io_multipart_threaded(operation_ , dataObj_and_IO, replica_token, hier_str, session, fname,
                           total_size, num_threads, **extra_options):
    """Called by _io_main.

    Carve up (0,total_size) range into `num_threads` parts and initiate a transfer thread for each one.
    """
    (Data_object, Io) = dataObj_and_IO
    Operation = Oper( operation_ )

    def bytes_range_for_thread( i, num_threads, total_bytes,  chunk ):
        begin_offs = i * chunk
        if i + 1 < num_threads:
            end_offs = (i + 1) * chunk
        else:
            end_offs = total_bytes
        return six.moves.range(begin_offs, end_offs)

    bytes_per_thread = total_size // num_threads

    ranges = [bytes_range_for_thread(i, num_threads, total_size, bytes_per_thread) for i in range(num_threads)]

    logger.info("num_threads = %s ; bytes_per_thread = %s", num_threads, bytes_per_thread)

    _queueLength = extra_options.get('_queueLength',0)
    if _queueLength > 0:
        queueObject = Queue(_queueLength)
    else:
        queueObject = None

    futures = []
    executor = concurrent.futures.ThreadPoolExecutor(max_workers = num_threads)
    num_threads = min(num_threads, len(ranges))
    mgr = _Multipart_close_manager(Io, Barrier(num_threads))
    counter = 1
    gen_file_handle = lambda: open(fname, Operation.disk_file_mode(initial_open = (counter == 1)))
    File = gen_file_handle()
    for byte_range in ranges:
        if Io is None:
            Io = session.data_objects.open( Data_object.path, Operation.data_object_mode(initial_open = False),
                                            create = False, finalize_on_close = False,
                                            **{ kw.NUM_THREADS_KW: str(num_threads),
                                                kw.DATA_SIZE_KW: str(total_size),
                                                kw.RESC_HIER_STR_KW: hier_str,
                                                kw.REPLICA_TOKEN_KW: replica_token })
        mgr.add_io( Io )
        if File is None: File = gen_file_handle()
        futures.append(executor.submit( _io_part, Io, byte_range, File, Operation, mgr, str(counter), queueObject))
        counter += 1
        Io = File = None

    if Operation.isNonBlocking():
        if _queueLength:
            return futures, queueObject, mgr
        else:
            return futures
    else:
        bytecounts = [ f.result() for f in futures ]
        return sum(bytecounts), total_size



def io_main( session, Data, opr_, fname, R='', **kwopt):
    """
    The entry point for parallel transfers (multithreaded PUT and GET operations).

    Here, we do the following:
    * instantiate the data object, if this has not already been done.
    * determine replica information and the appropriate number of threads.
    * call the multithread manager to initiate multiple data transfer threads

    """
    total_bytes = kwopt.pop('total_bytes', -1)
    Operation = Oper(opr_)
    d_path = None
    Io = None

    if isinstance(Data,tuple):
        (Data, Io) = Data[:2]

    if isinstance (Data, six.string_types):
        d_path = Data
        try:
            Data = session.data_objects.get( Data )
            d_path = Data.path
        except DataObjectDoesNotExist:
            if Operation.isGet(): raise

    R_via_libcall = kwopt.pop( 'target_resource_name', '')
    if R_via_libcall:
        R = R_via_libcall

    num_threads = kwopt.get( 'num_threads', None)
    if num_threads is None: num_threads = int(kwopt.get('N','0'))
    if num_threads < 1:
        num_threads = RECOMMENDED_NUM_THREADS_PER_TRANSFER
    num_threads = max(1, min(multiprocessing.cpu_count(), num_threads))

    open_options = {}
    if Operation.isPut():
        if R:
            open_options [kw.RESC_NAME_KW] = R
            open_options [kw.DEST_RESC_NAME_KW] = R
        open_options[kw.NUM_THREADS_KW] = str(num_threads)
        open_options[kw.DATA_SIZE_KW] = str(total_bytes)

    if (not Io):
        (Io, rawfile) = session.data_objects.open_with_FileRaw( (d_path or Data.path),
                                                                Operation.data_object_mode(initial_open = True),
                                                                finalize_on_close = True, **open_options )
    else:
        if type(Io) is deferred_call:
            Io[kw.NUM_THREADS_KW] = str(num_threads)
            Io[kw.DATA_SIZE_KW] =  str(total_bytes)
            Io = Io()
        rawfile = Io.raw

    # At this point, the data object's existence in the catalog is guaranteed,
    # whether the Operation is a GET or PUT.

    if not isinstance(Data,iRODSDataObject):
        Data = session.data_objects.get(d_path)

    # Determine total number of bytes for transfer.

    if Operation.isGet():
        total_bytes = Io.seek(0,os.SEEK_END)
        Io.seek(0,os.SEEK_SET)
    else: # isPut
        if total_bytes < 0:
            with open(fname, 'rb') as f:
                f.seek(0,os.SEEK_END)
                total_bytes = f.tell()

    # Get necessary info and initiate threaded transfers.

    (replica_token , resc_hier) = rawfile.replica_access_info()

    queueLength = kwopt.get('queueLength',0)
    retval = _io_multipart_threaded (Operation, (Data, Io), replica_token, resc_hier, session, fname, total_bytes,
                                     num_threads = num_threads,
                                     _queueLength = queueLength)

    # SessionObject.data_objects.parallel_{put,get} will return:
    #   - immediately with an AsyncNotify instance, if Oper.NONBLOCKING flag is used.
    #   - upon completion with a boolean completion status, otherwise.

    if Operation.isNonBlocking():

        if queueLength > 0:
            (futures, chunk_notify_queue, mgr) = retval
        else:
            futures = retval
            chunk_notify_queue = total_bytes = None

        return AsyncNotify( futures,                              # individual futures, one per transfer thread
                            progress_Queue = chunk_notify_queue,  # for notifying the progress indicator thread
                            total = total_bytes,                  # total number of bytes for parallel transfer
                            keep_ = {'mgr': mgr}  )   # an open raw i/o object needing to be persisted, if any
    else:
        (_bytes_transferred, _bytes_total) = retval
        return (_bytes_transferred == _bytes_total)

if __name__ == '__main__':

    import getopt
    import atexit
    from irods.session import iRODSSession

    def setupLoggingWithDateTimeHeader(name,level = logging.DEBUG):
        if _nullh in logger.handlers:
            logger.removeHandler(_nullh)
            if name:
                handler = logging.FileHandler(name)
            else:
                handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)-15s - %(message)s'))
        logger.addHandler(handler)
        logger.setLevel( level )

    try:
        env_file = os.environ['IRODS_ENVIRONMENT_FILE']
    except KeyError:
        env_file = os.path.expanduser('~/.irods/irods_environment.json')
    ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=None, capath=None, cadata=None)
    ssl_settings = {'ssl_context': ssl_context}
    sess = iRODSSession(irods_env_file=env_file, **ssl_settings)
    atexit.register(lambda : sess.cleanup())

    opt,arg = getopt.getopt( sys.argv[1:], 'vL:l:aR:N:')

    opts = dict(opt)

    logFilename = opts.pop('-L',None)  # '' for console, non-empty for filesystem destination
    logLevel = (logging.INFO if logFilename is None else logging.DEBUG)
    logFilename = logFilename or opts.pop('-l',None)

    if logFilename is not None:
        setupLoggingWithDateTimeHeader(logFilename, logLevel)

    verboseConnection = (opts.pop('-v',None) is not None)

    async_xfer = opts.pop('-a',None)

    kwarg = { k.lstrip('-'):v for k,v in opts.items() }

    arg[1] = Oper.PUT if arg[1].lower() in ('w','put','a') \
                      else Oper.GET
    if async_xfer is not None:
        arg[1] |= Oper.NONBLOCKING

    ret = io_main(sess, *arg, **kwarg) # arg[0] = data object or path
                                       # arg[1] = operation: or'd flags : [PUT|GET] NONBLOCKING
                                       # arg[2] = file path on local filesystem
                                       # kwarg['queueLength'] sets progress-queue length (0 if no progress indication needed)
                                       # kwarg options 'N' (num threads) and 'R' (target resource name) are via command-line
                                       # kwarg['num_threads'] (overrides 'N' when called as a library)
                                       # kwarg['target_resource_name'] (overrides 'R' when called as a library)
    if isinstance( ret, AsyncNotify ):
        print('waiting on completion...',file=sys.stderr)
        ret.set_transfer_done_callback(lambda r: print('Async transfer done for:',r,file=sys.stderr))
        done = ret.wait_until_transfer_done (timeout=10.0)  # - or do other useful work here
        if done:
            bytes_transferred = sum(ret.futures_done.values())
            print ('Asynch transfer complete. Total bytes transferred:', bytes_transferred,file=sys.stderr)
        else:
            print ('Asynch transfer was not completed before timeout expired.',file=sys.stderr)
    else:
        print('Synchronous transfer {}'.format('succeeded' if ret else 'failed'),file=sys.stderr)

# Note : This module requires concurrent.futures, included in Python3.x.
#        On Python2.7, this dependency must be installed using 'pip install futures'.
# Demonstration :
#
# $ dd if=/dev/urandom bs=1k count=150000 of=$HOME/puttest
# $ time python -m irods.parallel -R demoResc -N 3 `ipwd`/test.dat put $HOME/puttest  # add -v,-a for verbose, asynch
# $ time python -m irods.parallel -R demoResc -N 3 `ipwd`/test.dat get $HOME/gettest  # add -v,-a for verbose, asynch
# $ diff puttest gettest
