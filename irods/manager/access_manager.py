from os.path import basename, dirname

from irods.manager import Manager
from irods.data_object import iRODSDataObject
from irods.models import (DataObject, Collection, User, DataAccess)
from irods.access import iRODSAccess

import logging

logger = logging.getLogger(__name__)


class AccessManager(Manager):
    def get(self, path):

        conditions = [
                Collection.name == dirname(path), 
                DataObject.name == basename(path)
            ]

        results = self.sess.query(User.name, User.id, DataObject.id, DataAccess.name)\
            .filter(*conditions).all()

        return [iRODSAccess(
            access_name = row[DataAccess.name],
            user_id = row[User.id],
            data_id = row[DataObject.id],
            user_name = row[User.name]
        ) for row in results]
