import json
import sys

def run (CI):

    final_config = CI.store_config(
        {
            "yaml_substitutions": {       # -> written to ".env"
                "python_version" : "3",
                "client_os_generic": "ubuntu",
                "client_os_image": "ubuntu:18.04",
                "python_rule_engine_installed": "y"
            },
            "container_environments": {
                "client-runner" : {       # -> written to "client-runner.env"
                    "TESTS_TO_RUN": ""    # run test subset, e.g. "irods.test.data_obj_test"
                }

            }
        }
    )

    print ('----------\nconfig after CI modify pass\n----------',file=sys.stderr)
    print(json.dumps(final_config,indent=4),file=sys.stderr)

    return CI.run_and_wait_on_client_exit ()
