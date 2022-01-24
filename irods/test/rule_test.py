#! /usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import sys
import time
import textwrap
import unittest
from irods.models import DataObject
from irods.exception import (FAIL_ACTION_ENCOUNTERED_ERR, RULE_ENGINE_ERROR, UnknowniRODSError)
import irods.test.helpers as helpers
from irods.rule import Rule
import six
from io import open as io_open
import io


RE_Plugins_installed_run_condition_args = ( os.environ.get('PYTHON_RULE_ENGINE_INSTALLED','*').lower()[:1]=='y',
                                           'Test depends on server having Python-REP installed beyond the default options' )


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

    def test_set_metadata_288(self):

        session = self.sess

        # rule body
        rule_body = textwrap.dedent('''\
                                    *attribute.*attr_name = "*attr_value"
                                    msiAssociateKeyValuePairsToObj(*attribute, *object, "-d")
                                    # (: -- just a comment -- :)  writeLine("serverLog","*value")
                                    ''')

        input_params = { '*value': "3334" , "*object": '/tempZone/home/rods/runner.py' ,
                                          '*attr_name':'XX',
                                          '*attr_value':'YY'
        }

        output = 'ruleExecOut'

        myrule = Rule(session, body=rule_body, params=input_params, output=output)
        myrule.execute()


    # test catching fail-type actions initiated directly in the instance being called.
    #
    @unittest.skipUnless (*RE_Plugins_installed_run_condition_args)
    def test_with_fail_in_targeted_rule_engines(self):
        self._failing_in_targeted_rule_engines(rule_to_call = "generic_failing_rule")


    # test catching rule fail actions initiated using the native 'failmsg' microservice.
    #
    @unittest.skipUnless (*RE_Plugins_installed_run_condition_args)
    def test_with_using_native_fail_msvc(self):
        error_dict = \
        self._failing_in_targeted_rule_engines(rule_to_call = [('irods_rule_engine_plugin-python-instance','failing_with_message_py'),
                                                               ('irods_rule_engine_plugin-irods_rule_language-instance','failing_with_message')])
        for v in error_dict.values():
            self.assertIn('code of minus 2', v[1].args[0])

    # helper for the previous two tests.
    #
    def _failing_in_targeted_rule_engines(self, rule_to_call = None):
        session = self.sess
        if isinstance(rule_to_call,(list,tuple)):
            rule_dict = dict(rule_to_call)
        else:
            rule_dict = {}

        rule_instances_list = ( 'irods_rule_engine_plugin-irods_rule_language-instance',
                                'irods_rule_engine_plugin-python-instance' )
        err_hash = {}

        for i in rule_instances_list:

            if rule_dict:
                rule_to_call = rule_dict[i]

            rule = Rule( session, body = rule_to_call,
                         instance_name = i )
            try:
                rule.execute( acceptable_errors = (-1,) )
            except UnknowniRODSError as e:
                err_hash[i] = ('rule exec failed! - misc - ',(e)) # 2-tuple = failure
            except RULE_ENGINE_ERROR as e:
                err_hash[i] = ('rule exec failed! - python - ',(e)) # 2-tuple = failure
            except FAIL_ACTION_ENCOUNTERED_ERR as e:
                err_hash[i] = ('rule exec failed! - native - ',(e))
            else:
                err_hash[i] = ('rule exec succeeded!',) # 1-tuple = success

        self.assertEqual( len(err_hash), len(rule_instances_list) )
        self.assertEqual( len(err_hash), len([val for val in err_hash.values() if val[0].startswith('rule exec failed')]) )
        return err_hash


    @unittest.skipUnless (*RE_Plugins_installed_run_condition_args)
    def test_targeting_Python_instance_when_rule_multiply_defined(self):
        self._with_X_instance_when_rule_multiply_defined(
            instance_name  = 'irods_rule_engine_plugin-python-instance',
            test_condition = lambda bstring: b'python' in bstring
            )

    @unittest.skipUnless (*RE_Plugins_installed_run_condition_args)
    def test_targeting_Native_instance_when_rule_multiply_defined(self):
        self._with_X_instance_when_rule_multiply_defined(
            instance_name  = 'irods_rule_engine_plugin-irods_rule_language-instance',
            test_condition = lambda bstring: b'native' in bstring
            )

    @unittest.skipUnless (*RE_Plugins_installed_run_condition_args)
    def test_targeting_Unspecified_instance_when_rule_multiply_defined(self):
        self._with_X_instance_when_rule_multiply_defined(
            test_condition = lambda bstring: b'native' in bstring and b'python' in bstring
            )

    def _with_X_instance_when_rule_multiply_defined(self,**kw):
        session = self.sess
        rule = Rule( session, body = 'defined_in_both',
                     output = 'ruleExecOut',
                     **{key:val for key,val in kw.items() if key == 'instance_name'}
                   )
        output  = rule.execute()
        buf = output.MsParam_PI[0].inOutStruct.stdoutBuf.buf
        self.assertTrue(kw['test_condition'](buf.rstrip(b'\0').rstrip()))


    def test_specifying_rule_instance(self):

        self._with_writeline_to_stream(
                stream_name = 'stdout',
                rule_engine_instance = "irods_rule_engine_plugin-irods_rule_language-instance" )


    def _with_writeline_to_stream(self, stream_name = "serverLog",
                                          output_string = 'test-writeline-to-stream',
                                          alternate_input_params = (),
                                          rule_engine_instance = ""):

        session = self.sess

        # rule body
        rule_body = textwrap.dedent('''\
                                    writeLine("{stream_name}","*value")
                                    '''.format(**locals()))

        input_params = { '*value': output_string }
        input_params.update( alternate_input_params )

        output_param = 'ruleExecOut'

        extra_options = {}

        if rule_engine_instance:
            extra_options [ 'instance_name' ] = rule_engine_instance

        myrule = Rule(session, body=rule_body, params=input_params, output=output_param, **extra_options)
        output = myrule.execute()

        buf = None
        if stream_name == 'stdout':
            buf = output.MsParam_PI[0].inOutStruct.stdoutBuf.buf
        elif stream_name == 'stderr':
            buf = output.MsParam_PI[0].inOutStruct.stderrBuf.buf

        if buf is not None:
            buf = buf.decode('utf-8')
            self.assertEqual (output_string, buf.rstrip('\0').rstrip())


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
        myrule = Rule(session, body=rule_body, irods_3_literal_style = True,
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


    @staticmethod
    def lines_from_stdout_buf(output):
        buf = ""
        if output and len(output.MsParam_PI):
            buf = output.MsParam_PI[0].inOutStruct.stdoutBuf.buf
            if buf:
                buf = buf.rstrip(b'\0').decode('utf8')
        return buf.splitlines()


    def test_rulefile_in_file_like_object_1__336(self):

        rule_file_contents = textwrap.dedent(u"""\
        hw {
                helloWorld(*message);
                writeLine("stdout", "Message is: [*message] ...");
        }
        helloWorld(*OUT)
        {
          *OUT = "Hello world!"
        }
        """)
        r = Rule(self.sess, rule_file = io.StringIO( rule_file_contents ),
                            output = 'ruleExecOut', instance_name='irods_rule_engine_plugin-irods_rule_language-instance')
        output = r.execute()
        lines = self.lines_from_stdout_buf(output)
        self.assertRegexpMatches (lines[0], '.*\[Hello world!\]')


    def test_rulefile_in_file_like_object_2__336(self):

        rule_file_contents = textwrap.dedent("""\
        main {
          other_rule()
          writeLine("stdout","["++type(*msg2)++"][*msg2]");
        }
        other_rule {
          writeLine("stdout","["++type(*msg1)++"][*msg1]");
        }

        INPUT *msg1="",*msg2=""
        OUTPUT ruleExecOut
        """)

        r = Rule(self.sess, rule_file = io.BytesIO( rule_file_contents.encode('utf-8') ))
        output = r.execute()
        lines = self.lines_from_stdout_buf(output)
        self.assertRegexpMatches (lines[0], '\[STRING\]\[\]')
        self.assertRegexpMatches (lines[1], '\[STRING\]\[\]')

        r = Rule(self.sess, rule_file = io.BytesIO( rule_file_contents.encode('utf-8') )
                          , params = {'*msg1':5, '*msg2':'"A String"'})
        output = r.execute()
        lines = self.lines_from_stdout_buf(output)
        self.assertRegexpMatches (lines[0], '\[INTEGER\]\[5\]')
        self.assertRegexpMatches (lines[1], '\[STRING\]\[A String\]')


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
