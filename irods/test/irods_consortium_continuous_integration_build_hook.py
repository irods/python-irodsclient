from __future__ import print_function

import optparse
import os
import shutil

import irods_python_ci_utilities


def main(output_root_directory):
    run_tests()
    if output_root_directory:
        gather_xml_reports(output_root_directory)

def run_tests():
    # prerequisites
    install_testing_dependencies()
    irods_python_ci_utilities.subprocess_get_output(['sudo', 'cp', '-r', '/var/lib/irods/.irods', '/home/irodsbuild/'], check_rc=True)
    irods_python_ci_utilities.subprocess_get_output(['sudo', 'chown', '-R', 'irodsbuild', '/home/irodsbuild/.irods'], check_rc=True)
    irods_python_ci_utilities.subprocess_get_output(['sudo', 'chmod', '-R', '777', '/etc/irods'], check_rc=True)

    # test run
    test_env = os.environ.copy()
    test_env['IRODS_CI_TEST_RUN'] = '1'
    irods_python_ci_utilities.subprocess_get_output(['python-coverage', 'run', 'irods/test/runner.py'], env=test_env)

    # reports
    irods_python_ci_utilities.subprocess_get_output(['python-coverage', 'report'], check_rc=True)
    irods_python_ci_utilities.subprocess_get_output(['python-coverage', 'xml'], check_rc=True)

def install_testing_dependencies():
    dispatch_map = {
        'Ubuntu': install_testing_dependencies_apt,
    }
    try:
        return dispatch_map[irods_python_ci_utilities.get_distribution()]()
    except KeyError:
        irods_python_ci_utilities.raise_not_implemented_for_distribution()

def install_testing_dependencies_apt():
    irods_python_ci_utilities.install_os_packages(['git', 'python-prettytable', 'python-coverage', 'python-dev', 'libkrb5-dev'])
    irods_python_ci_utilities.subprocess_get_output(['sudo', '-H', 'pip', 'install', 'gssapi'], check_rc=True)

def gather_xml_reports(output_root_directory):
    irods_python_ci_utilities.mkdir_p(output_root_directory)
    shutil.copy('coverage.xml', output_root_directory)
    shutil.copytree('/tmp/python-irodsclient/test-reports', os.path.join(output_root_directory, 'test-reports'))

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('--output_root_directory')
    options, _ = parser.parse_args()

    main(options.output_root_directory)
