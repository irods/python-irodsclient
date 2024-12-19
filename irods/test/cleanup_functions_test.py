import os
import re
import subprocess
import sys
import textwrap
import unittest

import irods.at_client_exit
import irods.test.modules as test_modules


class TestCleanupFunctions(unittest.TestCase):

    def test_execution_of_client_exit_functions_at_proper_time__issue_614(self):
        helper_script = os.path.join(
            test_modules.__path__[0], "test_client_exit_functions.py"
        )

        # Note: The enum.Enum subclass's __members__ is an ordered dictionary, i.e. key order is preserved:
        #    https://docs.python.org/3.6/library/enum.html#iteration
        # This is essential for the test to pass, since:
        #    - We assume that key order to be preserved in the rendering of the arguments list presented to the test helper script.
        #    - That argument order determines the below-asserted order of execution, at script exit, of the functions registered therein.

        args = [""] + list(irods.at_client_exit.LibraryCleanupStage.__members__)

        p = subprocess.Popen(
            [sys.executable, helper_script, *args], stdout=subprocess.PIPE
        )
        script_output = p.communicate()[0].decode().strip()
        from irods.test.modules.test_client_exit_functions import (
            projected_output_from_innate_list_order,
        )

        self.assertEqual(projected_output_from_innate_list_order(args), script_output)

    def test_that_client_exit_functions_execute_in_LIFO_order_and_despite_uncaught_exceptions__issue_614(
        self,
    ):
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                textwrap.dedent(
                    """
            import logging
            logging.basicConfig()
            from irods.at_client_exit import (_register, LibraryCleanupStage, register_for_execution_before_prc_cleanup, register_for_execution_after_prc_cleanup)
            gen_lambda = lambda expressions: (lambda:[print(eval(x)) for x in expressions])

            register_for_execution_after_prc_cleanup(gen_lambda(['"after1"','1/0']))
            register_for_execution_after_prc_cleanup(gen_lambda(['"after2"','1/0']))

            _register(LibraryCleanupStage.DURING, gen_lambda(['"during"','1/0']))

            register_for_execution_before_prc_cleanup(gen_lambda(['"before"','1/0']))
            """
                ),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout_content, stderr_content = process.communicate()
        self.assertEqual(
            len(list(re.finditer(rb"ZeroDivisionError.*\n", stderr_content))), 4
        )
        self.assertEqual(
            b",".join([m.group() for m in re.finditer(rb"(\w+)", stdout_content)]),
            b"before,during,after2,after1",
        )

    def test_notifying_client_exit_functions_of_stage_in_which_they_are_called__issue_614(
        self,
    ):
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                textwrap.dedent(
                    """
            from irods.at_client_exit import (unique_function_invocation,
                get_stage, LibraryCleanupStage, NOTIFY_VIA_ATTRIBUTE,
                register_for_execution_before_prc_cleanup,
                register_for_execution_after_prc_cleanup)
            def before(): print(f'before:{get_stage().name}')
            def after(): print(f'after:{get_stage().name}')
            register_for_execution_before_prc_cleanup(unique_function_invocation(before), stage_notify_function = NOTIFY_VIA_ATTRIBUTE)
            register_for_execution_after_prc_cleanup(unique_function_invocation(after), stage_notify_function = NOTIFY_VIA_ATTRIBUTE)
            """
                ),
            ],
            stdout=subprocess.PIPE,
        )
        stdout_content, _ = process.communicate()
        stdout_lines = stdout_content.split(b"\n")
        self.assertIn(b"before:BEFORE", stdout_lines)
        self.assertIn(b"after:AFTER", stdout_lines)


if __name__ == "__main__":
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath("../.."))
    unittest.main()
