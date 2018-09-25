from __future__ import absolute_import
import logging

from irods.models import User, UserGroup
from irods.manager import Manager
from irods.message import GeneralAdminRequest, iRODSMessage
from irods.exception import UserDoesNotExist, UserGroupDoesNotExist, NoResultFound
from irods.api_number import api_number
from irods.user import iRODSUser, iRODSUserGroup
import irods.password_obfuscation as obf

logger = logging.getLogger(__name__)


class UserManager(Manager):

    def get(self, user_name, user_zone=""):
        query = self.sess.query(User).filter(User.name == user_name)

        if len(user_zone) > 0:
            query = query.filter(User.zone == user_zone)

        try:
            result = query.one()
        except NoResultFound:
            raise UserDoesNotExist()
        return iRODSUser(self, result)

    def create(self, user_name, user_type, user_zone="", auth_str=""):
        message_body = GeneralAdminRequest(
            "add",
            "user",
            user_name,
            user_type,
            user_zone,
            auth_str
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['GENERAL_ADMIN_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)
        return self.get(user_name, user_zone)

    def remove(self, user_name, user_zone=""):
        message_body = GeneralAdminRequest(
            "rm",
            "user",
            user_name,
            user_zone
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['GENERAL_ADMIN_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)

    def modify(self, user_name, option, new_value, user_zone=""):

        # must append zone to username for this API call
        if len(user_zone) > 0:
            user_name += "#" + user_zone

        with self.sess.pool.get_connection() as conn:

            # if modifying password, new value needs obfuscating
            if option == 'password':
                current_password = self.sess.pool.account.password
                new_value = obf.obfuscate_new_password(new_value, current_password, conn.client_signature)

            message_body = GeneralAdminRequest(
                "modify",
                "user",
                user_name,
                option,
                new_value,
                user_zone,
            )
            request = iRODSMessage("RODS_API_REQ", msg=message_body,
                                   int_info=api_number['GENERAL_ADMIN_AN'])

            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)


class UserGroupManager(UserManager):

    def get(self, name, user_zone=""):
        query = self.sess.query(UserGroup).filter(UserGroup.name == name)

        try:
            result = query.one()
        except NoResultFound:
            raise UserGroupDoesNotExist()
        return iRODSUserGroup(self, result)

    def create(self, name, user_type='rodsgroup', user_zone="", auth_str=""):
        message_body = GeneralAdminRequest(
            "add",
            "user",
            name,
            user_type,
            "",
            ""
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['GENERAL_ADMIN_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)
        return self.get(name)

    def getmembers(self, name):
        results = self.sess.query(User).filter(
            User.type != 'rodsgroup', UserGroup.name == name)
        return [iRODSUser(self, row) for row in results]

    def addmember(self, group_name, user_name, user_zone=""):
        message_body = GeneralAdminRequest(
            "modify",
            "group",
            group_name,
            "add",
            user_name,
            user_zone
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['GENERAL_ADMIN_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)

    def removemember(self, group_name, user_name, user_zone=""):
        message_body = GeneralAdminRequest(
            "modify",
            "group",
            group_name,
            "remove",
            user_name,
            user_zone
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['GENERAL_ADMIN_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)
