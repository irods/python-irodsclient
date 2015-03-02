from irods.models import User
from irods.resource_manager import ResourceManager
from irods.message import GeneralAdminRequest, iRODSMessage
from irods.exception import UserDoesNotExist, NoResultFound
from irods.api_number import api_number
from irods.user import iRODSUser

import logging

logger = logging.getLogger(__name__)

class UserManager(ResourceManager):
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

