from __future__ import print_function
from __future__ import absolute_import
import logging
from os.path import dirname, basename

from irods.manager import Manager
from irods.message import MetadataRequest, iRODSMessage, JSON_Message
from irods.api_number import api_number
from irods.models import (DataObject, Collection, Resource,
                          User, DataObjectMeta, CollectionMeta, ResourceMeta, UserMeta)
from irods.meta import iRODSMeta, AVUOperation


logger = logging.getLogger(__name__)


class InvalidAtomicAVURequest(Exception): pass


class MetadataManager(Manager):

    @staticmethod
    def _model_class_to_resource_type(model_cls):
        return {
            DataObject: 'd',
            Collection: 'C',
            Resource: 'R',
            User: 'u',
        }[model_cls]

    @staticmethod
    def _model_class_to_resource_description(model_cls):
        return {
            DataObject: 'data_object',
            Collection: 'collection',
            Resource: 'resource',
            User: 'user',
        }[model_cls]

    def get(self, model_cls, path):
        resource_type = self._model_class_to_resource_type(model_cls)
        model = {
            'd': DataObjectMeta,
            'C': CollectionMeta,
            'R': ResourceMeta,
            'u': UserMeta
        }[resource_type]
        conditions = {
            'd': [
                Collection.name == dirname(path),
                DataObject.name == basename(path)
            ],
            'C': [Collection.name == path],
            'R': [Resource.name == path],
            'u': [User.name == path]
        }[resource_type]
        results = self.sess.query(model.id, model.name, model.value, model.units)\
            .filter(*conditions).all()
        return [iRODSMeta(
            row[model.name],
            row[model.value],
            row[model.units],
            avu_id=row[model.id]
        ) for row in results]

    def add(self, model_cls, path, meta):
        # Avoid sending request with empty argument(s)
        if not(len(path) and len(meta.name) and len(meta.value)):
            raise ValueError('Empty value in ' + repr(meta))

        resource_type = self._model_class_to_resource_type(model_cls)
        message_body = MetadataRequest(
            "add",
            "-" + resource_type,
            path,
            meta.name,
            meta.value,
            meta.units
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['MOD_AVU_METADATA_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)

    def remove(self, model_cls, path, meta):
        resource_type = self._model_class_to_resource_type(model_cls)
        message_body = MetadataRequest(
            "rm",
            "-" + resource_type,
            path,
            meta.name,
            meta.value,
            meta.units
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['MOD_AVU_METADATA_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)

    def copy(self, src_model_cls, dest_model_cls, src, dest):
        src_resource_type = self._model_class_to_resource_type(src_model_cls)
        dest_resource_type = self._model_class_to_resource_type(dest_model_cls)
        message_body = MetadataRequest(
            "cp",
            "-" + src_resource_type,
            "-" + dest_resource_type,
            src,
            dest
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['MOD_AVU_METADATA_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)

    def set(self, model_cls, path, meta):
        resource_type = self._model_class_to_resource_type(model_cls)
        message_body = MetadataRequest(
            "set",
            "-" + resource_type,
            path,
            meta.name,
            meta.value,
            meta.units
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['MOD_AVU_METADATA_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)

    @staticmethod
    def _avu_operation_to_dict( op ):
        opJSON = { "operation": op.operation,
                   "attribute": op.avu.name,
                   "value": op.avu.value
        }
        if op.avu.units not in ("",None):
            opJSON["units"] = op.avu.units
        return opJSON

    def apply_atomic_operations(self, model_cls, path, *avu_ops):
        if not all(isinstance(op,AVUOperation) for op in avu_ops):
            raise InvalidAtomicAVURequest("avu_ops must contain 1 or more AVUOperations")
        request = {
            "entity_name": path,
            "entity_type": self._model_class_to_resource_description(model_cls),
            "operations" : [self._avu_operation_to_dict(op) for op in avu_ops]
        }
        self._call_atomic_metadata_api(request)

    def _call_atomic_metadata_api(self, request_text):
        with self.sess.pool.get_connection() as conn:
            request_msg = iRODSMessage("RODS_API_REQ",  JSON_Message( request_text, conn.server_version ),
                                       int_info=api_number['ATOMIC_APPLY_METADATA_OPERATIONS_APN'])
            conn.send( request_msg )
            response = conn.recv()
        response_msg = response.get_json_encoded_struct()
        logger.debug("in atomic_metadata, server responded with: %r",response_msg)

