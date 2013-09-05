#! /usr/bin/env python
import os
import sys
import unittest


class TestCollection(unittest.TestCase):

    def setUp(self):
        from irods.session import iRODSSession
        import config

        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)

    def test_collection(self):
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


if __name__ == "__main__":
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
