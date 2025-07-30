#! /usr/bin/env python

from datetime import datetime as _datetime
import os
import sys
import unittest

from irods.models import User, Collection
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
        A_ZONE_NAME = "otherZone"
        A_ZONE_USER = "alice"
        try:
            zoneB = session.zones.create(A_ZONE_NAME, "remote")
            zBuser = session.users.create(A_ZONE_USER, "rodsuser", A_ZONE_NAME, "")
            usercolls = [
                iRODSCollection(session.collections, result)
                for result in session.query(Collection).filter(
                    Collection.owner_name == zBuser.name
                    and Collection.owner_zone == zBuser.zone
                )
            ]
            self.assertEqual(
                [
                    (u[User.name], u[User.zone])
                    for u in session.query(User).filter(User.zone == A_ZONE_NAME)
                ],
                [(A_ZONE_USER, A_ZONE_NAME)],
            )
            zBuser.remove()
            zoneB.remove()
        finally:
            for p in usercolls:
                try:
                    session.collections.get(p.path)
                except CollectionDoesNotExist:
                    continue
                perm = iRODSAccess("own", p.path, session.username, session.zone)
                session.acls.set(perm, admin=True)
                p.remove(force=True)

    def test_create_common_username_remote_then_local__issue_764(self):
        zone = None
        users= []
        test_zone = "remote_zone"
        # TODO(#763): remove user name randomization.
        test_user = "user_issue_764_" + helpers.unique_name(helpers.my_function_name(), _datetime.now())
        try:
            zone = self.sess.zones.create(test_zone, "remote")
            users.append(
                self.sess.users.create(test_user, "rodsuser", user_zone=test_zone)
            )
            users.append(
                self.sess.users.create(test_user, "rodsuser", user_zone="")
            )
            self.assertEqual(2, len(list(self.sess.query(User).filter(User.name == test_user))))
        finally:
            for user in users:
                user.remove()
            if zone:
                zone.remove()

if __name__ == "__main__":
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath("../.."))
    unittest.main()
