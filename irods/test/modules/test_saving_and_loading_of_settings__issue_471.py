import sys
import os
import subprocess

import irods
import irods.client_configuration as config
from irods.test import modules as test_modules
from irods.test.modules.test_auto_close_of_data_objects__issue_456 import (
    auto_close_data_objects,
)


def test(truth_value):
    """Temporarily sets the data object auto-close setting true and launches a new interpreter
    to ensure the setting is auto-loaded.
    """
    program = os.path.join(test_modules.__path__[0], os.path.basename(__file__))
    try:
        os.putenv(irods.settings_path_environment_variable, "")
        with auto_close_data_objects(truth_value):
            config.save()
        # Call into this same module as a command.  This will cause another Python interpreter to start
        # up in a separate process and execute the function run_as_process() to test the saved setting.
        # We return from this function the output of that process, stripped of whitespace.
        process = subprocess.Popen([sys.executable, program], stdout=subprocess.PIPE)
        return process.communicate()[0].decode().strip()
    finally:
        os.unsetenv(irods.settings_path_environment_variable)
        os.unlink(config.DEFAULT_CONFIG_PATH)


def run_as_process():
    print(config.data_objects.auto_close)


if __name__ == "__main__":
    run_as_process()
