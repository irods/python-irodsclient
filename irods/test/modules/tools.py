import time

_clock_polling_interval = max(0.01, time.clock_getres(time.CLOCK_BOOTTIME))

LARGE_TEST_TIMEOUT = 10 * 60.0  # ten minutes.


def wait_till_true(callback, timeout=LARGE_TEST_TIMEOUT, msg=""):
    """Wait for test purposes until a condition becomes true , as determined by the
    return value of the provided test function.

    By default, we wait at most LARGE_TEST_TIMEOUT seconds for the callback function to return true,
    and then quit or time out.  Alternatively, a timeout of None translates as a request not to time out.

    If the msg value passed in is a nonzero-length string, it can be used to raise a timeout exception;
    otherwise timing out causes a normal exit, relaying as the return value the last value returned
    from the test callback function.
    """
    start_time = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    while not (truth_value := callback()):
        if (
            timeout is not None
            and (time.clock_gettime_ns(time.CLOCK_BOOTTIME) - start_time) * 1e-9
            > timeout
        ):
            if msg:
                raise TimeoutError(msg)
            else:
                break
        time.sleep(_clock_polling_interval)
    return truth_value
