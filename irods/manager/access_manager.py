from os.path import basename, dirname

from irods.manager import Manager
from irods.api_number import api_number
from irods.message import ModAclRequest, iRODSMessage
from irods.data_object import iRODSDataObject, irods_dirname, irods_basename
from irods.collection import iRODSCollection
from irods.models import (
    DataObject,
    Collection,
    User,
    CollectionUser,
    DataAccess,
    CollectionAccess,
)
from irods.access import iRODSAccess
from irods.column import In
from irods.user import iRODSUser

import logging
import warnings

logger = logging.getLogger(__name__)


def users_by_ids(session, ids=()):
    try:
        ids = list(iter(ids))
    except TypeError:
        if type(ids) in (str, int):
            ids = int(ids)
        else:
            raise
    cond = (
        ()
        if not ids
        else (
            (In(User.id, list(map(int, ids))),)
            if len(ids) > 1
            else (User.id == int(ids[0]),)
        )
    )
    return [
        iRODSUser(session.users, i)
        for i in session.query(User.id, User.name, User.type, User.zone).filter(*cond)
    ]


class AccessManager(Manager):

    def get(self, target, report_raw_acls=True, **kw):

        if report_raw_acls:
            return self.__get_raw(
                target, **kw
            )  # prefer a behavior consistent  with 'ils -A`

        # different query whether target is an object or a collection
        if type(target) == iRODSDataObject:
            access_type = DataAccess
            user_type = User
            conditions = [
                Collection.name == dirname(target.path),
                DataObject.name == basename(target.path),
            ]
        elif type(target) == iRODSCollection:
            access_type = CollectionAccess
            user_type = CollectionUser
            conditions = [Collection.name == target.path]
        else:
            raise TypeError

        results = (
            self.sess.query(user_type.name, user_type.zone, access_type.name)
            .filter(*conditions)
            ._all()
        )

        def get_usertype(row):
            return self.sess.users.get(row[user_type.name], row[user_type.zone]).type

        return [
            iRODSAccess(
                access_name=row[access_type.name],
                user_name=row[user_type.name],
                user_type=get_usertype(row),
                path=target.path,
                user_zone=row[user_type.zone],
            )
            for row in results
        ]

    def coll_access_query(self, path):
        return self.sess.query(Collection, CollectionAccess).filter(
            Collection.name == path
        )

    def data_access_query(self, path):
        cn = irods_dirname(path)
        dn = irods_basename(path)
        return self.sess.query(DataObject, DataAccess).filter(
            Collection.name == cn, DataObject.name == dn
        )

    def __get_raw(self, target, **kw):

        ### sample usage: ###
        #
        #  user_id_list = []  # simply to store the user id's from the discovered ACL's
        #  session.acls.get( data_or_coll_target, acl_users = user_id_list,
        #                                         acl_users_transform = lambda u: u.id)
        #
        # -> returns list of iRODSAccess objects mapping one-to-one with ACL's stored in the catalog

        users_out = kw.pop("acl_users", None)
        T = kw.pop("acl_users_transform", lambda value: value)

        # different choice of query based on whether target is an object or a collection
        if isinstance(target, iRODSDataObject):
            access_column = DataAccess
            query_func = self.data_access_query

        elif isinstance(target, iRODSCollection):
            access_column = CollectionAccess
            query_func = self.coll_access_query
        else:
            raise TypeError

        # TODO: remove the filtering through extant_ids on resolution of irods/irods#6921.
        #   (depending on the nature of the fix we may make it conditional, based on the server --
        #   if for example in upcoming iRODS 4.2.12 and >=4.3.1 outdated userIDs in R_OBJT_ACCESS
        #   are guaranteed to be systematically and atomically purged.
        extant_ids = set(u[User.id] for u in self.sess.query(User))
        rows = [
            r for r in query_func(target.path) if r[access_column.user_id] in extant_ids
        ]
        userids = set(r[access_column.user_id] for r in rows)

        user_lookup = {j.id: j for j in users_by_ids(self.sess, userids)}

        if isinstance(users_out, dict):
            users_out.update(user_lookup)
        elif isinstance(users_out, list):
            users_out += [T(v) for v in user_lookup.values()]
        elif isinstance(users_out, set):
            users_out |= set(T(v) for v in user_lookup.values())
        elif users_out is None:
            pass
        else:
            raise TypeError

        # Instantiate as set before converting to a list, in order to remove duplicate iRODSAccess
        # objects. [#557]

        acls = list(
            {
                iRODSAccess(
                    r[access_column.name],
                    target.path,
                    user_lookup[r[access_column.user_id]].name,
                    user_lookup[r[access_column.user_id]].zone,
                    user_lookup[r[access_column.user_id]].type,
                )
                for r in rows
            }
        )
        return acls

    def set(self, acl, recursive=False, admin=False, **kw):

        prefix = "admin:" if admin else ""

        userName_ = acl.user_name
        zone_ = acl.user_zone
        if acl.access_name.endswith("inherit"):
            zone_ = userName_ = ""
        acl = acl.copy(decanonicalize=True)
        message_body = ModAclRequest(
            recursiveFlag=int(recursive),
            accessLevel=f"{prefix}{acl.access_name}",
            userName=userName_,
            zone=zone_,
            path=acl.path,
        )
        request = iRODSMessage(
            "RODS_API_REQ",
            msg=message_body,
            int_info=api_number["MOD_ACCESS_CONTROL_AN"],
        )
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)
