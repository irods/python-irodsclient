import datetime
import os
import re
import signal
import subprocess
import sys
import irods.helpers
from irods.session import iRODSSession
from irods.test.helpers import unique_name
from irods.test import modules as test_modules
from irods.parallel import abort_parallel_transfers

OBJECT_SIZE = 4 * 1024**3
LOCAL_TEMPFILE_NAME = "data_object_for_issue_722.dat"


def test(test_case, signal_names=("SIGTERM", "SIGINT")):
    """Creates a child process executing a long put() and ensures the process can be terminated using SIGINT or SIGTERM."""
    from .tools import wait_till_true

    program = os.path.join(test_modules.__path__[0], os.path.basename(__file__))
    session = getattr(test_case, "sess", None) or irods.helpers.make_session()

    for signal_name in signal_names:

        with test_case.subTest(f"Testing with signal {signal_name}"):

            try:
                # Call into this same module as a command.  This will initiate another Python process that
                # performs a lengthy data object "get" operation (see the main body of the script, below.)
                process = subprocess.Popen(
                    # -k: Keep object around for replica status testing.
                    [sys.executable, program, "-k"],
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    text=True,
                )

                # Wait for download process to reach the point of spawning data transfer threads.  In Python 3.9+ versions
                # of the concurrent.futures module, these are non-daemon threads and will block the exit of the main thread
                # unless measures are taken.
                logical_path = process.stdout.readline().strip()

                # Use timeout of 10 minutes for test transfer, which should be more than enough.
                test_case.assertTrue(
                    wait_till_true(
                        lambda: session.data_objects.exists(logical_path)
                        and named_irods_data_object(
                            session, logical_path, delete=False
                        ).data.size
                        > OBJECT_SIZE // 2,
                    ),
                    "Parallel download from data_objects.put() probably experienced a fatal error before spawning auxiliary data transfer threads.",
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

                # Assert that the status is left as not LOCKED.
                test_case.assertTrue(
                    wait_till_true(
                        lambda: int(
                            session.data_objects.get(logical_path).replica_status
                        )
                        < 2
                    )
                )

            finally:
                if logical_path and (
                    d := irods.helpers.get_data_object(session, logical_path)
                ):
                    d.unlink(force=True)


class named_irods_data_object:

    def __init__(self, /, session: iRODSSession, path: str = "", delete: bool = True):
        self.sess = session
        self.delete = delete
        if not path:
            path = (
                irods.helpers.home_collection(session)
                + "/"
                + unique_name(datetime.datetime.now())
            )
        self.path = path

    @property
    def data(self):
        return irods.helpers.get_data_object(self.sess, self.path)

    def __del__(self):
        if self.delete:
            self.remove()

    def remove(self):
        if d := self.data:
            d.unlink(force=True)

    def create(self):
        self.sess.data_objects.create(self.path)
        return self


if __name__ == "__main__":
    import getopt

    opts, _ = getopt.getopt(sys.argv[1:], "k")
    keep_data_object = "-k" in (_[0] for _ in opts)

    # These lines are run only if the module is launched as a process.
    test_session = irods.helpers.make_session()
    hc = irods.helpers.home_collection(test_session)
    TESTFILE_FILL = b"_" * (1024 * 1024)

    object_path = named_irods_data_object(test_session, delete=True).create().path
    local_path = object_path.split("/")[-1]

    # Create the object to uploaded.
    with open(local_path, "wb") as f:
        for y in range(OBJECT_SIZE // len(TESTFILE_FILL)):
            f.write(TESTFILE_FILL)

    try:
        # Tell the parent process the name of the data object logical path, the target of the "put" to iRODS.
        # That parent process is the unittest, which will use the logical path to verify the threads are started
        # and we're somewhere mid-transfer.
        print(object_path)
        sys.stdout.flush()

        def handler(sig, *_):
            abort_parallel_transfers()
            if sig == signal.SIGTERM:
                os._exit(128 + sig)

        signal.signal(signal.SIGTERM, handler)

        try:
            # Upload the object
            test_session.data_objects.put(local_path, object_path)
        except KeyboardInterrupt:
            abort_parallel_transfers()
            raise

    finally:
        # Clean up, whether or not the upload succeeded.
        if local_path is not None and os.path.exists(local_path):
            os.unlink(local_path)
        if not keep_data_object:
            named_irods_data_object(test_session, path=object_path, delete=True)
