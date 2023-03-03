from __future__ import absolute_import
import logging
import os
import warnings

from irods.models import User, Group
from irods.manager import Manager
from irods.message import UserAdminRequest, GeneralAdminRequest, iRODSMessage, GetTempPasswordForOtherRequest, GetTempPasswordForOtherOut
from irods.exception import UserDoesNotExist, GroupDoesNotExist, NoResultFound, CAT_SQL_ERR
from irods.api_number import api_number
from irods.user import iRODSUser, iRODSGroup
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

    def create_with_password(self, user_name, password, user_zone = ''):
        """This method can be used by a groupadmin to initialize the password field while creating the new user.
           (This is necessary since group administrators may not change the password of an existing user.)
        """

        message_body = UserAdminRequest(
                "mkuser", user_name, "" if not password else \
                                     obf.obfuscate_new_password_with_key(password, self.sess.pool.account.password)
                )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['USER_ADMIN_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)
        return self.get(user_name, user_zone)


    def create(self, user_name, user_type, user_zone="", auth_str=""):
        message_body = GeneralAdminRequest(
            "add",
            "user",
            user_name if not user_zone or user_zone == self.sess.zone \
                      else "{}#{}".format(user_name,user_zone),
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

    def temp_password_for_user(self, user_name):
        with self.sess.pool.get_connection() as conn:
            message_body = GetTempPasswordForOtherRequest(
                targetUser=user_name,
                unused=None
            )
            request = iRODSMessage("RODS_API_REQ", msg=message_body,
                                   int_info=api_number['GET_TEMP_PASSWORD_FOR_OTHER_AN'])

            # Send request
            conn.send(request)

            # Receive answer
            try:
                response = conn.recv()
                logger.debug(response.int_info)
            except CAT_SQL_ERR:
                raise UserDoesNotExist()

            # Convert and return answer
            msg = response.get_main_message(GetTempPasswordForOtherOut)
            return obf.create_temp_password(msg.stringToHashWith, conn.account.password)


    class EnvStoredPasswordNotEdited(RuntimeError):

        """
        Error thrown by a password change attempt if a login password encoded in the
        irods environment could not be updated.

        This error will be seen when `modify_irods_authentication_file' is set True and the
        authentication scheme in effect for the session is other than iRODS native,
        using a password loaded from the client environment.
        """

        pass

    @staticmethod
    def abspath_exists(path):
        return (isinstance(path,str) and
                os.path.isabs(path) and
                os.path.exists(path))

    def modify_password(self, old_value, new_value, modify_irods_authentication_file = False):

        """
        Change the password for the current user (in the manner of `ipasswd').

        Parameters:
            old_value - the currently valid (old) password
            new_value - the desired (new) password
            modify_irods_authentication_file - Can be False, True, or a string.  If a string, it should indicate
                                  the absolute path of an IRODS_AUTHENTICATION_FILE to be altered.
        """
        with self.sess.pool.get_connection() as conn:

            hash_new_value = obf.obfuscate_new_password(new_value, old_value, conn.client_signature)

            message_body = UserAdminRequest(
                "userpw",
                self.sess.username,
                "password",
                hash_new_value
            )
            request = iRODSMessage("RODS_API_REQ", msg=message_body,
                                   int_info=api_number['USER_ADMIN_AN'])

            conn.send(request)
            response = conn.recv()
            if modify_irods_authentication_file:
                auth_file = self.sess.auth_file
                if not auth_file or isinstance(modify_irods_authentication_file, str):
                    auth_file = (modify_irods_authentication_file if self.abspath_exists(modify_irods_authentication_file) else '')
                if not auth_file:
                    message = "Session not loaded from an environment file."
                    raise UserManager.EnvStoredPasswordNotEdited(message)
                else:
                    with open(auth_file) as f:
                        stored_pw = obf.decode(f.read())
                    if stored_pw != old_value:
                        message = "Not changing contents of '{}' - "\
                                  "stored password is non-native or false match to old password".format(auth_file)
                        raise UserManager.EnvStoredPasswordNotEdited(message)
                    with open(auth_file,'w') as f:
                        f.write(obf.encode(new_value))

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


class GroupManager(UserManager):

    def get(self, name, user_zone=""):
        query = self.sess.query(Group).filter(Group.name == name)

        try:
            result = query.one()
        except NoResultFound:
            raise GroupDoesNotExist()
        return iRODSGroup(self, result)

    def _api_info(self, group_admin_flag):
        """
        If group_admin_flag is:         then use UserAdminRequest API:
        ---------------------------     ------------------------------
        True                            always
        False (user_groups default)     never
        None  (groups default)          when user type is groupadmin
        """

        sess = self.sess
        if group_admin_flag or (group_admin_flag is not False and sess.users.get(sess.username).type == 'groupadmin'):
            return (UserAdminRequest, 'USER_ADMIN_AN')
        return (GeneralAdminRequest, 'GENERAL_ADMIN_AN')

    def create(self, name,
               user_type = 'rodsgroup',
               user_zone = "",
               auth_str = "",
               group_admin = False, **options):

        if not options.pop('suppress_deprecation_warning', False):
            warnings.warn('Use of session.user_groups is deprecated in v1.1.7 - prefer session.groups',
                          DeprecationWarning, stacklevel = 2)

        (MessageClass, api_key) = self._api_info(group_admin)
        api_to_use = api_number[api_key]

        if MessageClass is UserAdminRequest:
            message_body = MessageClass(
                "mkgroup",
                name,
                user_type,
                user_zone
            )
        else:
            message_body = MessageClass(
                "add",
                "user",
                name,
                user_type,
                "",
                ""
            )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_to_use)
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)
        return self.get(name)

    def getmembers(self, name):
        results = self.sess.query(User).filter(
            User.type != 'rodsgroup', Group.name == name)
        return [iRODSUser(self, row) for row in results]

    def addmember(self, group_name,
                        user_name,
                        user_zone = "",
                        group_admin = False, **options):

        if not options.pop('suppress_deprecation_warning', False):
            warnings.warn('Use of session.user_groups is deprecated in v1.1.7 - prefer session.groups',
                          DeprecationWarning, stacklevel = 2)

        (MessageClass, api_key) = self._api_info(group_admin)

        message_body = MessageClass(
            "modify",
            "group",
            group_name,
            "add",
            user_name,
            user_zone
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number[api_key])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)

    def removemember(self,
                     group_name,
                     user_name,
                     user_zone = "",
                     group_admin = False, **options):

        if not options.pop('suppress_deprecation_warning', False):
            warnings.warn('Use of session.user_groups is deprecated in v1.1.7 - prefer session.groups',
                          DeprecationWarning, stacklevel = 2)

        (MessageClass, api_key) = self._api_info(group_admin)

        message_body = MessageClass(
            "modify",
            "group",
            group_name,
            "remove",
            user_name,
            user_zone
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number[api_key])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)


# NOTE: Everything of the form *UserGroup* is deprecated.
UserGroupManager = GroupManager
