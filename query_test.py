#! /usr/bin/env python2.6
from irods.session import iRODSSession
from irods.query import Query
from irods.models import User, Collection, Keywords
import logging

q1 = Query(None, User, Collection.name)
q2 = q1.filter(User.name == 'cjlarose')
q3 = q2.filter(Keywords.chksum == '12345')

logging.debug(q1.columns)
logging.debug(q1.criteria)

logging.debug(q2.columns)
logging.debug(q2.criteria)

logging.debug(q3.columns)
logging.debug(q3.criteria)

logging.debug(q3._select_message().pack())

f = open('select', 'w')
f.write(q3._select_message().pack())

f = open('conds', 'w')
f.write(q3._conds_message().pack())

f = open('condskw', 'w')
f.write(q3._kw_message().pack())
