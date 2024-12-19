# This helper module can double as a Python script, allowing us to run the below
# test() method either within the current process or in a child process.  The
# method in question can thus be called by the following unit tests so that we may assert
# proper data object auto-closing functionality under these respective scenarios:
#
#    irods.test.data_obj_test.TestDataObjOps.test_data_objects_auto_close_on_function_exit__issue_456
#    irods.test.data_obj_test.TestDataObjOps.test_data_objects_auto_close_on_process_exit__issue_456

import contextlib

try:
    import irods.client_configuration as config
except ImportError:
    pass
from datetime import datetime
import os
from irods.test import helpers


@contextlib.contextmanager
def auto_close_data_objects(value):
    if "config" not in globals():
        yield
        return
    ORIGINAL_VALUE = config.data_objects.auto_close
    try:
        config.data_objects.auto_close = value
        yield
    finally:
        config.data_objects.auto_close = ORIGINAL_VALUE


def test(return_locals=True):
    with auto_close_data_objects(True):
        expected_content = "content"
        ses = helpers.make_session()
        name = "/{0.zone}/home/{0.username}/{1}-object.dat".format(
            ses, helpers.unique_name(os.getpid(), datetime.now())
        )
        f = ses.data_objects.open(name, "w")
        f.write(expected_content.encode("utf8"))
        L = locals()
        # By default, ses and f will be automatically exported to calling frame (with L being returned),
        # but by specifying a list/tuple of keys we can export only those specific locals by name.
        return (
            L
            if not isinstance(return_locals, (tuple, list))
            else [L[k] for k in return_locals]
        )


if __name__ == "__main__":
    test_output = test()
    print("{name} {expected_content}".format(**test_output))
