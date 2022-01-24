from __future__ import absolute_import
from irods.message import iRODSMessage, StringStringMap, RodsHostAddress, STR_PI, MsParam, MsParamArray, RuleExecutionRequest
from irods.api_number import api_number
import irods.exception as ex
from io import open as io_open
from irods.message import Message, StringProperty
import six

class RemoveRuleMessage(Message):
    #define RULE_EXEC_DEL_INP_PI "str ruleExecId[NAME_LEN];"
    _name = 'RULE_EXEC_DEL_INP_PI'
    ruleExecId = StringProperty()
    def __init__(self,id_):
        super(RemoveRuleMessage,self).__init__()
        self.ruleExecId = str(id_)

class Rule(object):
    def __init__(self, session, rule_file=None, body='', params=None, output='', instance_name = None, irods_3_literal_style = False):
        """
        Initialize a rule object.

        Arguments:
        Use one of:
          * rule_file : the name of an existing file containint "rule script" style code. In the context of
            the native iRODS Rule Language, this is a file ending in '.r' and containing iRODS rules.
            Optionally, this parameter can be a file-like object containing the rule script text.
          * body: the text of block of rule code (possibly including rule calls) to be run as if it were
            the body of a rule, e.g. the part between the braces of a rule definition in the iRODS rule language.
        * instance_name: the name of the rule engine instance in the context of which to run the rule(s).
        * output may be set to 'ruleExecOut' if console output is expected on stderr or stdout streams.
        * params are key/value pairs to be sent into a rule_file.
        * irods_3_literal_style: affects the format of the @external directive. Use `True' for iRODS 3.x.

        """
        self.session = session

        self.params = {}
        self.output = ''

        if rule_file:
            self.load(rule_file)
        else:
            self.body = '@external\n' + body if irods_3_literal_style \
                   else '@external rule { ' + body + ' }'

        # overwrite params and output if received arguments
        if isinstance( params , dict ):
            if self.params:
                self.params.update( params )
            else:
                self.params = params

        if output != '':
            self.output = output

        self.instance_name = instance_name

    def remove_by_id(self,*ids):
        with self.session.pool.get_connection() as conn:
            for id_ in ids:
                request = iRODSMessage("RODS_API_REQ", msg=RemoveRuleMessage(id_),
                                       int_info=api_number['RULE_EXEC_DEL_AN'])
                conn.send(request)
                response = conn.recv()
                if response.int_info != 0:
                    raise RuntimeError("Error removing rule {id_}".format(**locals()))

    def load(self, rule_file, encoding = 'utf-8'):
        """Load rule code with rule-file (*.r) semantics.

        A "main" rule is defined first; name does not matter. Other rules may follow, which will be
        callable from the first rule.  Any rules defined in active rule-bases within the server are
        also callable.

        The `rule_file' parameter is a filename or file-like object.  We give it either:
           - a string holding the path to a rule-file in the local filesystem, or
           - an in-memory object (eg. io.StringIO or io.BytesIO) whose content is that of a rule-file.

        This addresses a regression in v1.1.0; see issue #336.  In v1.1.1+, if rule code is passed in literally via
        the `body' parameter of the Rule constructor, it is interpreted as if it were the body of a rule, and
        therefore it may not contain internal rule definitions.  However, if rule code is submitted as the content
        of a file or file-like object referred to by the `rule_file' parameter of the Rule constructor, will be
        interpreted as .r-file content.  Therefore, it must contain a main rule definition first, followed
        possibly by others which will be callable from the main rule as if they were part of the core rule-base.

        """
        self.body = '@external\n'


        with (io_open(rule_file, encoding = encoding) if isinstance(rule_file,six.string_types) else rule_file
        ) as f:

            # parse rule file line-by-line
            for line in f:

                # convert input line to Unicode if necessary
                if isinstance(line, bytes):
                    line = line.decode(encoding)

                # parse input line
                if line.strip().lower().startswith('input'):

                    input_header, input_line = line.split(None, 1)

                    if input_line.strip().lower() == 'null':
                        self.params = {}
                        continue

                    # sanity check
                    if input_header.lower() != 'input':
                        raise ValueError

                    # parse *param0="value0",*param1="value1",...
                    for pair in input_line.split(','):
                        label, value = pair.split('=')
                        self.params[label.strip()] = value.strip()

                # parse output line
                elif line.strip().lower().startswith('output'):
                    output_header, output_line = line.split(None, 1)

                    # sanity check
                    if output_header.lower() != 'output':
                        raise ValueError

                    # use line as is
                    self.output = output_line.strip()

                # parse rule
                else:
                    self.body += line


    def execute(self, session_cleanup = True,
                      acceptable_errors = (ex.FAIL_ACTION_ENCOUNTERED_ERR,),
                      r_error = None,
                      return_message = ()):
        try:
            # rule input
            param_array = []
            for label, value in self.params.items():
                inOutStruct = STR_PI(myStr=value)
                param_array.append(MsParam(label=label, type='STR_PI', inOutStruct=inOutStruct))

            inpParamArray = MsParamArray(paramLen=len(param_array), oprType=0, MsParam_PI=param_array)

            # rule body
            addr = RodsHostAddress(hostAddr='', rodsZone='', port=0, dummyInt=0)
            condInput = StringStringMap( {} if self.instance_name is None
                                            else {'instance_name':self.instance_name} )
            message_body = RuleExecutionRequest(myRule=self.body, addr=addr, condInput=condInput, outParamDesc=self.output, inpParamArray=inpParamArray)

            request = iRODSMessage("RODS_API_REQ", msg=message_body, int_info=api_number['EXEC_MY_RULE_AN'])

            with self.session.pool.get_connection() as conn:
                conn.send(request)
                response = conn.recv(acceptable_errors = acceptable_errors, return_message = return_message)
                try:
                    out_param_array = response.get_main_message(MsParamArray, r_error = r_error)
                except iRODSMessage.ResponseNotParseable:
                    return MsParamArray() # Ergo, no useful return value - but the RError stack will be accessible
        finally:
            if session_cleanup:
                self.session.cleanup()

        return out_param_array
