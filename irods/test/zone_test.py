#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import unittest

from irods.models import User,Collection
from irods.access import iRODSAccess
from irods.collection import iRODSCollection
from irods.exception import CollectionDoesNotExist
import irods.test.helpers as helpers

class TestRemoteZone(unittest.TestCase):

    def setUp(self):
        self.sess = helpers.make_session()

    def tearDown(self):
        """Close connections."""
        self.sess.cleanup()

    # This test should pass whether or not federation is configured:
    def test_create_other_zone_user_227_228(self):
        usercolls = []
        session = self.sess
        A_ZONE_NAME = 'otherZone'
        A_ZONE_USER = 'alice'
        try:
            zoneB =  session.zones.create(A_ZONE_NAME,'remote')
            zBuser = session.users.create(A_ZONE_USER,'rodsuser', A_ZONE_NAME, '')
            usercolls = [ iRODSCollection(session.collections, result) for result in
                          session.query(Collection).filter(Collection.owner_name == zBuser.name and 
                                                     Collection.owner_zone == zBuser.zone) ]
            self.assertEqual ([(u[User.name],u[User.zone]) for u in session.query(User).filter(User.zone == A_ZONE_NAME)],
                              [(A_ZONE_USER,A_ZONE_NAME)])
            zBuser.remove()
            zoneB.remove()
        finally:
            for p in usercolls:
                try:
                    session.collections.get( p.path )
                except CollectionDoesNotExist:
                    continue
                perm = iRODSAccess( 'own', p.path, session.username, session.zone)
                session.permissions.set( perm, admin=True)
                p.remove(force=True)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
