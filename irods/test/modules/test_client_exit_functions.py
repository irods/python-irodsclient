#  Used in test of:
#    irods.test.cleanup_functions_test.TestCleanupFunctions.test_proper_execution_of_client_exit_functions__issue_614

import irods.at_client_exit
import sys


def get_stage_object_and_value_from_name(stage_name):
    try:
        obj = getattr(irods.at_client_exit.LibraryCleanupStage, stage_name)
        return obj, obj.value
    except AttributeError:
        return None, stage_name


def object_printer(name, stream=sys.stdout):
    (obj, _) = get_stage_object_and_value_from_name(stage_name=name)
    return lambda: print(f"[{name if not obj else obj.value}]", end="", file=stream)


def projected_output_from_innate_list_order(name_list):
    import io

    in_memory_stream = io.StringIO()
    for name in name_list:
        func = object_printer(name, stream=in_memory_stream)
        func()
    return in_memory_stream.getvalue()


# When run as :
#     $ test_client_exit_functions.py "misc_string" "STAGE_NAME_1" "STAGE_NAME_2" ...
# this script transforms the argv vector into an output of the form:
#    [misc_string][<STAGE_NAME_1.value>][<STAGE_NAME_2.value>]...
# where the value attribute is the STAGE_NAME_x's assigned enum value.
# The square brackets are literal.
# As indicated, any string (including the empty string) that does not name a
# particular stage name is left untransformed.

if __name__ == "__main__":

    function_info = [
        [*get_stage_object_and_value_from_name(name), object_printer(name)]
        for name in reversed(sys.argv[1:])
    ]

    # For each argument to the script that represents a cleanup stage: register a function to print the stage's value, to be run during that stage.
    for key in function_info.copy():
        (stage, name, func) = key
        if not stage:
            continue
        irods.at_client_exit._register(stage, func)
        function_info.remove(key)

    # Immediately execute any leftover functions, since the test expects the corresponding output to precede that of their counterparts run during cleanup.
    for stage, name, func in function_info:
        func()
