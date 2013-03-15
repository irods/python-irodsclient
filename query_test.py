#! /usr/bin/env python2.6
from irods.session import iRODSSession
from irods.query import Query
from irods.models import User, Collection
import logging

q1 = Query(None, User, Collection.name)
q2 = q1.filter(User.name == 'cjlarose')

logging.debug(q1.columns)
logging.debug(q1.criteria)

logging.debug(q2.columns)
logging.debug(q2.criteria)
