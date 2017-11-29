from __future__ import absolute_import
from irods.models import Resource
from irods.manager import Manager
from irods.message import GeneralAdminRequest, iRODSMessage
from irods.exception import ResourceDoesNotExist, NoResultFound, OperationNotSupported
from irods.api_number import api_number
from irods.resource import iRODSResource

import logging

logger = logging.getLogger(__name__)


class ResourceManager(Manager):

    @staticmethod
    def serialize(context):
        if isinstance(context, dict):
            return ';'.join("{}={}".format(key, value) for (key, value) in list(context.items()))
        return context

    def get(self, name, zone=""):
        query = self.sess.query(Resource).filter(Resource.name == name)

        if len(zone) > 0:
            query = query.filter(Resource.zone_name == zone)

        try:
            result = query.one()
        except NoResultFound:
            raise ResourceDoesNotExist()
        return iRODSResource(self, result)

    def create(self, name, resource_type, host="EMPTY_RESC_HOST", path="EMPTY_RESC_PATH", context="", zone="", resource_class=""):
        with self.sess.pool.get_connection() as conn:
            # check server version
            if conn.server_version < (4, 0, 0):
                # make resource, iRODS 3 style
                message_body = GeneralAdminRequest(
                    "add",
                    "resource",
                    name,
                    resource_type,
                    resource_class,
                    host,
                    path,
                    zone
                )
            else:
                message_body = GeneralAdminRequest(
                    "add",
                    "resource",
                    name,
                    resource_type,
                    host + ":" + path,
                    self.serialize(context),
                    zone
                )

            request = iRODSMessage("RODS_API_REQ", msg=message_body,
                                   int_info=api_number['GENERAL_ADMIN_AN'])

            conn.send(request)
            response = conn.recv()
            self.sess.cleanup()
            # close connections to get new agents with up to
            # date resource manager

        logger.debug(response.int_info)
        return self.get(name, zone)

    def remove(self, name, test=False):
        if test:
            mode = "--dryrun"
        else:
            mode = ""
        message_body = GeneralAdminRequest(
            "rm",
            "resource",
            name,
            mode
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['GENERAL_ADMIN_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
            self.sess.cleanup()
            # close connections to get new agents with up to
            # date resource manager
        logger.debug(response.int_info)

    def modify(self, name, attribute, value):
        with self.sess.pool.get_connection() as conn:
            message_body = GeneralAdminRequest(
                "modify",
                "resource",
                name,
                attribute,
                self.serialize(value)
            )

            request = iRODSMessage("RODS_API_REQ", msg=message_body,
                                   int_info=api_number['GENERAL_ADMIN_AN'])

            conn.send(request)
            response = conn.recv()
            self.sess.cleanup()
        logger.debug(response.int_info)
        return self.get(name)

    def add_child(self, parent, child, context=""):
        with self.sess.pool.get_connection() as conn:
            # check server version
            if conn.server_version < (4, 0, 0):
                # No resource hierarchies before iRODS 4
                raise OperationNotSupported

            message_body = GeneralAdminRequest(
                "add",
                "childtoresc",
                parent,
                child,
                context
            )

            request = iRODSMessage("RODS_API_REQ", msg=message_body,
                                   int_info=api_number['GENERAL_ADMIN_AN'])

            conn.send(request)
            response = conn.recv()
            self.sess.cleanup()
            # close connections to get new agents with up to
            # date resource manager
        logger.debug(response.int_info)

    def remove_child(self, parent, child):
        with self.sess.pool.get_connection() as conn:
            # check server version
            if conn.server_version < (4, 0, 0):
                # No resource hierarchies before iRODS 4
                raise OperationNotSupported

            message_body = GeneralAdminRequest(
                "rm",
                "childfromresc",
                parent,
                child
            )

            request = iRODSMessage("RODS_API_REQ", msg=message_body,
                                   int_info=api_number['GENERAL_ADMIN_AN'])

            conn.send(request)
            response = conn.recv()
            self.sess.cleanup()
            # close connections to get new agents with up to
            # date resource manager
        logger.debug(response.int_info)
