#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import socket
import unittest
import irods.test.config as config
from irods.session import iRODSSession


@unittest.skipIf(config.IRODS_SERVER_VERSION < (4, 0, 0), "iRODS 4+")
class TestSession(unittest.TestCase):

    def test_session_from_env_file(self):
        '''
        Open a session using a client irods environment file for credentials
        '''

        env_file = os.path.expanduser('~/.irods/irods_environment.json')

        if not os.access(env_file, os.R_OK):
            self.skipTest('No readable irods environment file')

        with iRODSSession(irods_env_file=env_file) as session:
            # do something with our session
            default_resource = session.resources.get('demoResc')
            self.assertEqual(default_resource.type, 'unixfilesystem')


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
