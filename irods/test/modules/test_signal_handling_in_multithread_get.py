
import os
import re
import signal
import subprocess
import sys
import tempfile
import time

import irods
import irods.helpers
from irods.test import modules as test_modules

OBJECT_SIZE = 2*1024**3
OBJECT_NAME = 'data_get_issue__722'
LOCAL_TEMPFILE_NAME = 'data_object_for_issue_722.dat'


_clock_polling_interval = max(.01, time.clock_getres(time.CLOCK_BOOTTIME))


def wait_till_true(function, timeout=None):
    start_time = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    while not (truth_value := function()):
        if timeout is not None and (time.clock_gettime_ns(time.CLOCK_BOOTTIME)-start_time)*1e-9 > timeout:
            break
        time.sleep(_clock_polling_interval)
    return truth_value


def test(test_case, signal_names = ("SIGTERM",#"SIGINT" 
            )):
    """Creates a child process executing a long get() and ensures the process can be
    terminated using SIGINT or SIGTERM.
    """
    program = os.path.join(test_modules.__path__[0], os.path.basename(__file__))

    for signal_name in signal_names:
        # Call into this same module as a command.  This will initiate another Python process that
        # performs a lengthy data object "get" operation (see the main body of the script, below.)
        process = subprocess.Popen([sys.executable, program],
                                   stderr=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   text = True)

        # Wait for download process to reach the point of spawning data transfer threads.  In Python 3.9+ versions
        # of the concurrent.futures module, these are nondaemon threads and will block the exit of the main thread
        # unless measures are taken (#722).
        localfile = process.stdout.readline().strip()
        test_case.assertTrue(wait_till_true(lambda:os.path.exists(localfile) and os.stat(localfile).st_size > OBJECT_SIZE//2),
                   "Parallel download from data_objects.get() probably experienced a fatal error before spawning auxiliary data transfer threads."
                  )

        signal_message_info = f"While testing signal {signal_name}"
        sig = getattr(signal, signal_name)

        # Interrupt the subprocess with the given signal.
        process.send_signal(sig)
        # Assert that this signal is what killed the subprocess, rather than a timed out process "wait" or a natural exit 
        # due to misproper or incomplete handling of the signal.
        try:
            test_case.assertEqual(process.wait(timeout = 15), -sig, "{signal_message_info}: unexpected subprocess return code.")
        except subprocess.TimeoutExpired as timeout_exc:
            test_case.fail(f"{signal_message_info}:  subprocess timed out before terminating.  "
                "Non-daemon thread(s) probably prevented subprocess's main thread from exiting.")
        # Assert that in the case of SIGINT, the process registered a KeyboardInterrupt.
        if sig == signal.SIGINT:
            test_case.assertTrue(re.search('KeyboardInterrupt', process.stderr.read()), 
                "{signal_message_info}: Expected 'KeyboardInterrupt' in log output.")


if __name__ == "__main__":
    # These lines are run only if the module is launched as a process.
    session = irods.helpers.make_session()
    hc = irods.helpers.home_collection(session)
    TESTFILE_FILL = b'_'*(1024*1024)
    object_path = f'{hc}/{OBJECT_NAME}'

    # Create the object to be downloaded.
    with session.data_objects.open(object_path,'w') as f:
        for y in range(OBJECT_SIZE//len(TESTFILE_FILL)):
            f.write(TESTFILE_FILL)
    local_path = None
    # Establish where (ie absolute path) to place the downloaded file, i.e. the  get() target.
    try:
        with tempfile.NamedTemporaryFile(prefix='local_file_issue_722.dat', delete = True) as t:
            local_path = t.name

        # Tell the parent process the name of the local file being "get"ted (got) from iRODS
        print(local_path)
        sys.stdout.flush()

        # "get" the object
        session.data_objects.get(object_path, local_path)
    finally:
        # Clean up, whether or not the download succeeded.
        if local_path is not None and os.path.exists(local_path):
            os.unlink(local_path)
        if session.data_objects.exists(object_path):
            session.data_objects.unlink(object_path, force=True)
