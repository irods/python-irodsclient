import struct
import logging
from . import MAX_SQL_ATTR


class MainMessage(object):
    def pack(self):
        raise NotImplementedError("Should be called from a subclass")

#define StartupPack_PI "int irodsProt; int reconnFlag; int connectCnt; str proxyUser[NAME_LEN]; str proxyRcatZone[NAME_LEN]; str clientUser[NAME_LEN]; str clientRcatZone[NAME_LEN]; str relVersion[NAME_LEN]; str apiVersion[NAME_LEN]; str option[NAME_LEN];"
class StartupPack(MainMessage):
    def __init__(self, user=None, zone=None):
        self.user = user
        self.zone = zone

    def pack(self):
        str = """<StartupPack_PI>
        <irodsProt>0</irodsProt>
        <connectCnt>0</connectCnt>
        <proxyUser>%s</proxyUser>
        <proxyRcatZone>%s</proxyRcatZone>
        <clientUser>%s</clientUser>
        <clientRcatZone>%s</clientRcatZone>
        <relVersion>rods3.2</relVersion>
        <apiVersion>d</apiVersion>
        <option></option>
        </StartupPack_PI>""" % (self.user, self.zone, self.user, self.zone)
        return str

#define authResponseInp_PI "bin *response(RESPONSE_LEN); str *username;"
class AuthResponseInp(MainMessage):
    def __init__(self, encoded_pwd=None, user=None):
        self.pwd = encoded_pwd
        self.user = user

    def pack(self):
        return self.pwd + self.user + '\x00' 

#define InxIvalPair_PI "int iiLen; int *inx(iiLen); int *ivalue(iiLen);"
class InxIvalPair(MainMessage):
    def __init__(self, data):
        self.data = data

    def pack(self):
        length = len(self.data)
        inx = self.data.keys()
        ival = self.data.values()

        items = []
        items.append(struct.pack(">i", length))
        items += [struct.pack(">i", i) for i in (inx + ival)]
        logging.debug(items)
        return "".join(items)

#define InxValPair_PI "int isLen; int *inx(isLen); str *svalue[isLen];" 
class InxValPair(MainMessage):
    def __init__(self, data):
        self.data = data

    def pack(self):
        length = len(self.data)
        inx = self.data.keys()
        ival = self.data.values()

        items = []
        items.append(struct.pack(">i", length))
        items += [struct.pack(">i", i) for i in inx]
        logging.debug(items)

        values = "\x00".join(ival) + "\x00" if length > 0 else ""
        logging.debug(values)

        return "".join(items) + values
        
#define KeyValPair_PI "int ssLen; str *keyWord[ssLen]; str *svalue[ssLen];"
class KeyValPair(MainMessage):
    def __init__(self, data):
        self.data = data

    def pack(self):
        length = len(self.data)
        keys = self.data.keys()
        vals = self.data.values()

        len_pack = struct.pack(">i", length)
        if length > 0:
            keys_pack = "\x00".join(keys) + "\x00"
            values_pack = "\x00".join(vals) + "\x00"
            return len_pack + keys_pack + values_pack
        else:
            return len_pack

#define GenQueryInp_PI "int maxRows; int continueInx; int partialStartIndex; int options; struct KeyValPair_PI; struct InxIvalPair_PI; struct InxValPair_PI;"
class GenQueryInp(MainMessage):
    def __init__(self, limit, cond_kw, select, cond, options, offset, \
        continue_index):
        self.limit = limit
        self.cond_kw = cond_kw
        self.select = select
        self.cond = cond
        self.options = options
        self.offset = offset
        self.continue_index = continue_index

    def pack(self):
        items = [struct.pack(">i", i) for i in \
            [self.limit, self.continue_index, self.offset, self.options]
        ]
        items += [self.cond_kw.pack(), self.select.pack(), self.cond.pack()]
        return "".join(items)

#define SqlResult_PI "int attriInx; int reslen; str *value(rowCnt)(reslen);"  
class SqlResult(MainMessage):
    def __init__(self, attribute_index, result_length, values):
        self.attribute_index = attribute_index
        self.result_length = result_length
        self.values = values

#define GenQueryOut_PI "int rowCnt; int attriCnt; int continueInx; int totalRowCount; struct SqlResult_PI[MAX_SQL_ATTR];"
class GenQueryOut(MainMessage):
    def __init__(self, row_count, attribute_count, continue_index, \
        total_row_count, sql_results):
        self.row_count = row_count
        self.attribute_count = attribute_count
        self.continue_index = continue_index
        self.total_row_count = total_row_count
        self.sql_results = sql_results

    @staticmethod
    def unpack(str):
        row_count, attribute_count, continue_index, total_row_count = \
            struct.unpack(">iiii", str[:16])

        i = 16
        sql_results = []
        for col_num in range(attribute_count):
            logging.debug(col_num)
            attribute_index, result_length = struct.unpack(">ii", str[i:i+8])
            i += 8
            start = i
            null_count = 0
            while null_count < row_count:
                if str[i] == '\x00':
                    null_count = null_count + 1
                i = i + 1
            values = str[start:i-1].split('\x00')
            sql_results.append(SqlResult(attribute_index, result_length, values))

        logging.debug(sql_results)

        return GenQueryOut(row_count, attribute_count, continue_index, \
            total_row_count, sql_results)

#define SpecColl_PI "int collClass; int type; str collection[MAX_NAME_LEN]; str objPath[MAX_NAME_LEN]; str resource[NAME_LEN]; str phyPath[MAX_NAME_LEN]; str cacheDir[MAX_NAME_LEN]; int cacheDirty; int replNum;"

#define DataObjInp_PI "str objPath[MAX_NAME_LEN]; int createMode; int openFlags; double offset; double dataSize; int numThreads; int oprType; struct *SpecColl_PI; struct KeyValPair_PI;"
# I have no idea what SpecColl_PI means
class DataObjInp(MainMessage):
    def __init__(self, path=None, create_mode=0, open_flags=0, offset=0, \
        data_size=0, num_threads=0, opr_type=0, key_vals=None):
        self.path = path
        self.create_mode = create_mode
        self.open_flags = open_flags
        self.offset = offset
        self.data_size = data_size
        self.num_threads = num_threads
        self.opr_type = opr_type
        self.key_vals = key_vals

    def pack(self):
        parts = []
        parts.append(self.path + '\x00')
        parts.append(struct.pack(">iiqqii", self.create_mode, self.open_flags, \
            self.offset, self.data_size, self.num_threads, self.opr_type))
        if self.key_vals:
            parts.append(self.key_vals.pack())
        return "".join(parts)
