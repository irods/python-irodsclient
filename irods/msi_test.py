#!/usr/bin/env python

from irods.session import iRODSSession

sess = iRODSSession(host="data.cyverse.org",port=1247,user="dingrod",password='dingrod',zone="iplant")

sess.miscsvrinfo()
