from __future__ import absolute_import
import logging

from irods.models import Zone
from irods.zone import iRODSZone
from irods.manager import Manager
from irods.message import GeneralAdminRequest, iRODSMessage
from irods.api_number import api_number
from irods.exception import ZoneDoesNotExist, NoResultFound

logger = logging.getLogger(__name__)

class ZoneManager(Manager):

    def get(self, zone_name):
        query = self.sess.query(Zone).filter(Zone.name == zone_name)

        try:
            result = query.one()
        except NoResultFound:
            raise ZoneDoesNotExist()
        return iRODSZone(self, result)

    def create(self, zone_name, zone_type):
        message_body = GeneralAdminRequest(
            "add",
            "zone",
            zone_name,
            zone_type,
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['GENERAL_ADMIN_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)
        return self.get(zone_name)

    def remove(self, zone_name):
        message_body = GeneralAdminRequest(
            "rm",
            "zone",
            zone_name
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['GENERAL_ADMIN_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)
