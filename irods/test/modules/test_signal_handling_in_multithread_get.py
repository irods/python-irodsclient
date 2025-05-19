import os
import re
import signal
import subprocess
import sys
import tempfile

import irods.helpers
from irods.test import modules as test_modules
from irods.parallel import abort_parallel_transfers

OBJECT_SIZE = 4 * 1024**3
OBJECT_NAME = "data_get_issue__722"
LOCAL_TEMPFILE_NAME = "data_object_for_issue_722.dat"


def test(test_case, signal_names=("SIGTERM", "SIGINT")):
    """Creates a child process executing a long get() and ensures the process can be
    terminated using SIGINT or SIGTERM.
    """
    from .tools import wait_till_true

    program = os.path.join(test_modules.__path__[0], os.path.basename(__file__))

    for signal_name in signal_names:

        with test_case.subTest(f"Testing with signal {signal_name}"):

            # Call into this same module as a command.  This will initiate another Python process that
            # performs a lengthy data object "get" operation (see the main body of the script, below.)
            process = subprocess.Popen(
                [sys.executable, program],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
            )

            # Wait for download process to reach the point of spawning data transfer threads.  In Python 3.9+ versions
            # of the concurrent.futures module, these are nondaemon threads and will block the exit of the main thread
            # unless measures are taken.
            localfile = process.stdout.readline().strip()
            # Use timeout of 10 minutes for test transfer, which should be more than enough.
            test_case.assertTrue(
                wait_till_true(
                    lambda: os.path.exists(localfile)
                    and os.stat(localfile).st_size > OBJECT_SIZE // 2,
                ),
                "Parallel download from data_objects.get() probably experienced a fatal error before spawning auxiliary data transfer threads.",
            )

            sig = getattr(signal, signal_name)

            signal_offset_return_code = lambda s: 128 - s if s < 0 else s
            signal_plus_128 = lambda sig: 128 + sig

            # Interrupt the subprocess with the given signal.
            process.send_signal(sig)

            # Assert that this signal is what killed the subprocess, rather than a timed out process "wait" or a natural exit
            # due to misproper or incomplete handling of the signal.
            try:
                translated_return_code = signal_offset_return_code(
                    process.wait(timeout=15)
                )
                test_case.assertIn(
                    translated_return_code,
                    [1, signal_plus_128(sig)],
                    f"Expected subprocess return code of {signal_plus_128(sig) = }; got {translated_return_code = }",
                )
            except subprocess.TimeoutExpired:
                test_case.fail(
                    "Subprocess timed out before terminating.  "
                    "Non-daemon thread(s) probably prevented subprocess's main thread from exiting."
                )
            # Assert that in the case of SIGINT, the process registered a KeyboardInterrupt.
            if sig == signal.SIGINT:
                test_case.assertTrue(
                    re.search("KeyboardInterrupt", process.stderr.read()),
                    "Did not find expected string 'KeyboardInterrupt' in log output.",
                )


if __name__ == "__main__":
    # These lines are run only if the module is launched as a process.
    session = irods.helpers.make_session()
    hc = irods.helpers.home_collection(session)
    TESTFILE_FILL = b"_" * (1024 * 1024)
    object_path = f"{hc}/{OBJECT_NAME}"

    # Create the object to be downloaded.
    with session.data_objects.open(object_path, "w") as f:
        for y in range(OBJECT_SIZE // len(TESTFILE_FILL)):
            f.write(TESTFILE_FILL)
    local_path = None
    # Establish where (ie absolute path) to place the downloaded file, i.e. the  get() target.
    try:
        with tempfile.NamedTemporaryFile(
            prefix="local_file_issue_722.dat", delete=True
        ) as t:
            local_path = t.name

        # Tell the parent process the name of the local file, ie the result of the "get" from iRODS.
        # That parent process is the unittest, which will use the filename to verify the threads are started
        # and we're somewhere mid-transfer.
        print(local_path)
        sys.stdout.flush()

        def handler(sig, *_):
            abort_parallel_transfers()
            if sig == signal.SIGTERM:
                os._exit(128 + sig)

        signal.signal(signal.SIGTERM, handler)

        try:
            # download the object
            session.data_objects.get(object_path, local_path)
        except KeyboardInterrupt:
            abort_parallel_transfers()
            raise

    finally:
        # Clean up, whether or not the download succeeded.
        if local_path is not None and os.path.exists(local_path):
            os.unlink(local_path)
        if session.data_objects.exists(object_path):
            session.data_objects.unlink(object_path, force=True)
