#! /usr/bin/env python2.6
from irods.session import iRODSSession
from irods.query import Query
from irods.models import User, Collection

query = Query(None, User, Collection.name)
