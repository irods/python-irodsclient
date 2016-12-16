#! /usr/bin/env python
import os
import sys
import time
import textwrap
import unittest
from irods.session import iRODSSession
from irods.models import DataObject
import irods.test.config as config
import irods.test.helpers as helpers
from irods.rule import Rule


class TestRule(unittest.TestCase):

    '''Suite of tests on rule operations
    '''

    def setUp(self):
        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)

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

        object_path = "/{zone}/home/{username}/{object_name}".format(**locals())
        object = helpers.make_object(session, object_path)

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
        object.unlink(force=True)

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

        object_path = "/{zone}/home/{username}/{object_name}".format(**locals())
        object = helpers.make_object(session, object_path)

        # rule body
        rule_body = textwrap.dedent('''\
                                test {{
                                    # add metadata
                                    *attribute.*name = *value;
                                    msiAssociateKeyValuePairsToObj(*attribute, *object, "-d")
                                }}''')

        # rule parameters
        input_params = {# extra quotes for string literals
                  '*object': '"{object_path}"'.format(**locals()),
                  '*name': '"{attr_name}"'.format(**locals()),
                  '*value': '"{attr_value}"'.format(**locals())
                  }
        output = 'ruleExecOut'

        # run test rule
        myrule = Rule(session, body=rule_body, params=input_params, output=output)
        myrule.execute()

        # check that metadata is there
        meta = session.metadata.get(DataObject, object_path)
        assert meta[0].name == attr_name
        assert meta[0].value == attr_value

        # remove test object
        object.unlink(force=True)


    def test_retrieve_stdout_from_rule(self):
        '''
        Tests running a rule from a client-side .r file.
        The rule writes things to its stdout that we
        get back on the client side
        '''
        session = self.sess

        # test metadata
        some_string = "foo"
        some_other_string = "bar"

        # make rule file
        ts = time.time()
        rule_file_path = "/tmp/test_{ts}.r".format(**locals())
        rule = textwrap.dedent('''\
                                test {{
                                    # write stuff
                                    writeLine("stdout", *some_string);
                                    writeLine("stdout", *some_other_string);
                                    writeLine("stdout", "boo");
                                }}
                                INPUT *some_string="{some_string}",*some_other_string="{some_other_string}"
                                OUTPUT ruleExecOut'''.format(**locals()))

        with open(rule_file_path, "w") as rule_file:
            rule_file.write(rule)

        # run test rule
        myrule = Rule(session, rule_file_path)
        out_array = myrule.execute()

        # check that we got our strings back
        buf = out_array.MsParam_PI[0].inOutStruct.stdoutBuf.buf
        self.assertIn(some_string, buf)
        self.assertIn(some_other_string, buf)

        # remove rule file
        os.remove(rule_file_path)



if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
