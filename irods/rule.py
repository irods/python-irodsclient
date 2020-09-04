from __future__ import absolute_import
from irods.message import iRODSMessage, StringStringMap, RodsHostAddress, STR_PI, MsParam, MsParamArray, RuleExecutionRequest
from irods.api_number import api_number
from io import open as io_open

class Rule(object):
    def __init__(self, session, rule_file=None, body='', params=None, output=''):
        self.session = session

        self.params = {}
        self.output = ''

        if rule_file:
            self.load(rule_file)
        else:
            self.body = '@external\n' + body

        # overwrite params and output if received arguments
        if params is not None:
            self.params = params
        if output != '':
            self.output = output

    def load(self, rule_file, encoding = 'utf-8'):
        self.body = '@external\n'

        # parse rule file
        with io_open(rule_file, encoding = encoding) as f:
            for line in f:
                # parse input line
                if line.strip().lower().startswith('input'):
                    input_header, input_line = line.split(None, 1)

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


    def execute(self):
        # rule input
        param_array = []
        for label, value in self.params.items():
            inOutStruct = STR_PI(myStr=value)
            param_array.append(MsParam(label=label, type='STR_PI', inOutStruct=inOutStruct))

        inpParamArray = MsParamArray(paramLen=len(param_array), oprType=0, MsParam_PI=param_array)

        # rule body
        addr = RodsHostAddress(hostAddr='', rodsZone='', port=0, dummyInt=0)
        condInput = StringStringMap({})
        message_body = RuleExecutionRequest(myRule=self.body, addr=addr, condInput=condInput, outParamDesc=self.output, inpParamArray=inpParamArray)

        request = iRODSMessage("RODS_API_REQ", msg=message_body, int_info=api_number['EXEC_MY_RULE_AN'])

        with self.session.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
            out_param_array = response.get_main_message(MsParamArray)
            self.session.cleanup()
        return out_param_array
