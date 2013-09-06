#! /usr/bin/env python2.6
import unittest
import os
import sys


class TestQuery(unittest.TestCase):
    """
    """

    def setUp(self):
        from irods.session import iRODSSession
        import config

        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,  # 4444 why?
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)

    def test_query(self):
        #from irods.query import Query
        from irods.models import User, Collection, Keywords

        q1 = self.sess.query(User, Collection.name)
        q2 = q1.filter(User.name == 'cjlarose')
        q3 = q2.filter(Keywords.chksum == '12345')

        f = open('select', 'w')
        f.write(q3._select_message().pack())

        f = open('conds', 'w')
        f.write(q3._conds_message().pack())

        f = open('condskw', 'w')
        f.write(q3._kw_message().pack())

        f = open('genq', 'w')
        f.write(q3._message().pack())

        self.sess.query(Collection.id, Collection.name).all()

        """
        cut-n-pasted from collection_test...
        """
        from irods.models import Collection, User, DataObject

        #q1 = sess.query(Collection.id).filter(Collection.name == "'/tempZone/home/rods'")
        #q1.all()

        #f = open('collquery', 'w')
        #f.write(q1._message().pack())

        #result = sess.query(Collection.id, Collection.owner_name, User.id, User.name)\
        #    .filter(Collection.owner_name == "'rods'")\
        #    .all()

        result = self.sess.query(DataObject.id, DataObject.collection_id, DataObject.name, User.name, Collection.name).all()

        print str(result)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
