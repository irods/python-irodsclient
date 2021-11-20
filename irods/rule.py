from __future__ import absolute_import
from irods.message import iRODSMessage, StringStringMap, RodsHostAddress, STR_PI, MsParam, MsParamArray, RuleExecutionRequest
from irods.api_number import api_number
import irods.exception as ex
from io import open as io_open
from irods.message import Message, StringProperty

class RemoveRuleMessage(Message):
    #define RULE_EXEC_DEL_INP_PI "str ruleExecId[NAME_LEN];"
    _name = 'RULE_EXEC_DEL_INP_PI'
    ruleExecId = StringProperty()
    def __init__(self,id_):
        super(RemoveRuleMessage,self).__init__()
        self.ruleExecId = str(id_)

class Rule(object):
    def __init__(self, session, rule_file=None, body='', params=None, output='', instance_name = None, irods_3_literal_style = False):
        self.session = session

        self.params = {}
        self.output = ''

        if rule_file:
            self.load(rule_file)
        else:
            self.body = '@external\n' + body if irods_3_literal_style \
                   else '@external rule { ' + body + ' }'

        # overwrite params and output if received arguments
        if params is not None:
            self.params = (self.params or params)
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
        self.body = '@external\n'

        # parse rule file
        with io_open(rule_file, encoding = encoding) as f:
            for line in f:
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
                      r_error_stack = None,
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
                response = conn.recv(acceptable_errors = acceptable_errors, return_message = return_message, use_rounded_code = True)
                try:
                    out_param_array = response.get_main_message(MsParamArray, r_error = r_error_stack)
                except iRODSMessage.ResponseNotParseable:
                    return MsParamArray() # Ergo, no useful return value - but the RError stack will be accessible
        finally:
            if session_cleanup:
                self.session.cleanup()

        return out_param_array
