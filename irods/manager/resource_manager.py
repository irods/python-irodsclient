from irods.models import Resource
from irods.manager import Manager
from irods.message import GeneralAdminRequest, iRODSMessage
from irods.exception import ResourceDoesNotExist, NoResultFound
from irods.api_number import api_number
from irods.resource import iRODSResource

import logging

logger = logging.getLogger(__name__)

class ResourceManager(Manager):
    def get(self, resource_name, resource_zone=""):
        query = self.sess.query(Resource).filter(Resource.name == resource_name)
        
        if len(resource_zone) > 0:
            query = query.filter(Resource.zone_name == resource_zone)
        
        try:
            result = query.one()
        except NoResultFound:
            raise ResourceDoesNotExist()
        return iRODSResource(self, result)
