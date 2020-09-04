#! /usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import sys
import time
import textwrap
import unittest
from irods.models import DataObject
import irods.test.helpers as helpers
from irods.rule import Rule
import six
from io import open as io_open


class TestRule(unittest.TestCase):

    '''Suite of tests on rule operations
    '''

    def setUp(self):
        self.sess = helpers.make_session()

    def tearDown(self):
        # close connections
        self.sess.cleanup()

    def test_add_metadata_from_rule_file(self):
        '''
        Tests running a rule from a client-side .r file.
        The rule adds metadata attributes to an iRODS object
        and we check for the presence of said attributes.
        '''
        session = self.sess

        # test metadata
        attr_name = "test_attr"
        attr_value = "test_value"

        # make test object
        ts = time.time()
        zone = session.zone
        username = session.username
        object_name = 'foo_{ts}.txt'.format(**locals())

        object_path = "/{zone}/home/{username}/{object_name}".format(
            **locals())
        obj = helpers.make_object(session, object_path)

        # make rule file
        rule_file_path = "/tmp/test_{ts}.r".format(**locals())
        rule = textwrap.dedent('''\
                                test {{
                                    # add metadata
                                    *attribute.*name = *value;
                                    msiAssociateKeyValuePairsToObj(*attribute, *object, "-d")
                                }}
                                INPUT *object="{object_path}",*name="{attr_name}",*value="{attr_value}"
                                OUTPUT ruleExecOut'''.format(**locals()))

        with open(rule_file_path, "w") as rule_file:
            rule_file.write(rule)

        # run test rule
        myrule = Rule(session, rule_file_path)
        myrule.execute()

        # check that metadata is there
        meta = session.metadata.get(DataObject, object_path)
        assert meta[0].name == attr_name
        assert meta[0].value == attr_value

        # remove test object
        obj.unlink(force=True)

        # remove rule file
        os.remove(rule_file_path)

    def test_add_metadata_from_rule(self):
        '''
        Runs a rule whose body and input parameters are created in our script.
        The rule adds metadata attributes to an iRODS object
        and we check for the presence of said attributes.
        '''
        session = self.sess

        # test metadata
        attr_name = "test_attr"
        attr_value = "test_value"

        # make test object
        ts = time.time()
        zone = session.zone
        username = session.username
        object_name = 'foo_{ts}.txt'.format(**locals())

        object_path = "/{zone}/home/{username}/{object_name}".format(
            **locals())
        obj = helpers.make_object(session, object_path)

        # rule body
        rule_body = textwrap.dedent('''\
                                test {{
                                    # add metadata
                                    *attribute.*name = *value;
                                    msiAssociateKeyValuePairsToObj(*attribute, *object, "-d")
                                }}''')

        # rule parameters
        input_params = {  # extra quotes for string literals
            '*object': '"{object_path}"'.format(**locals()),
            '*name': '"{attr_name}"'.format(**locals()),
            '*value': '"{attr_value}"'.format(**locals())
        }
        output = 'ruleExecOut'

        # run test rule
        myrule = Rule(session, body=rule_body,
                      params=input_params, output=output)
        myrule.execute()

        # check that metadata is there
        meta = session.metadata.get(DataObject, object_path)
        assert meta[0].name == attr_name
        assert meta[0].value == attr_value

        # remove test object
        obj.unlink(force=True)

    def test_retrieve_std_streams_from_rule(self):
        '''
        Tests running a rule from a client-side .r file.
        The rule writes things to its stdout that we
        get back on the client side
        '''

        # Wrong buffer length on older versions
        if self.sess.server_version < (4, 1, 7):
            self.skipTest('For iRODS 4.1.7 and newer')

        session = self.sess

        # test metadata
        some_string = u'foo'
        some_other_string = u'我喜欢麦当劳'
        err_string = u'⛔'

        # make rule file
        ts = time.time()
        rule_file_path = "/tmp/test_{ts}.r".format(**locals())
        rule = textwrap.dedent(u'''\
                                test {{
                                    # write stuff
                                    writeLine("stdout", *some_string);
                                    writeLine("stdout", *some_other_string);
                                    writeLine("stderr", *err_string);
                                }}
                                INPUT *some_string="{some_string}",*some_other_string="{some_other_string}",*err_string="{err_string}"
                                OUTPUT ruleExecOut'''.format(**locals()))

        with io_open(rule_file_path, "w", encoding='utf-8') as rule_file:
            rule_file.write(rule)

        # run test rule
        myrule = Rule(session, rule_file_path)
        out_array = myrule.execute()

        # retrieve out buffer
        buf = out_array.MsParam_PI[0].inOutStruct.stdoutBuf.buf

        # it's binary data (BinBytesBuf) so must be decoded
        buf = buf.decode('utf-8')

        # check that we get our strings back
        self.assertIn(some_string, buf)
        self.assertIn(some_other_string, buf)

        # same thing stderr buffer
        buf = out_array.MsParam_PI[0].inOutStruct.stderrBuf.buf

        # decode and check
        buf = buf.decode('utf-8')
        self.assertIn(err_string, buf)

        # remove rule file
        os.remove(rule_file_path)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
