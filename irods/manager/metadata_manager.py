import logging
import copy
from os.path import dirname, basename
from typing import Any, Dict

from irods.manager import Manager
from irods.message import MetadataRequest, iRODSMessage, JSON_Message
from irods.api_number import api_number
from irods.models import (
    DataObject,
    Collection,
    Resource,
    User,
    DataObjectMeta,
    CollectionMeta,
    ResourceMeta,
    UserMeta,
)
from irods.meta import iRODSMeta, AVUOperation
import irods.keywords as kw


logger = logging.getLogger(__name__)


class InvalidAtomicAVURequest(Exception):
    pass


class MetadataManager(Manager):

    @property
    def use_timestamps(self):
        return getattr(self, "_use_ts", False)

    __kw : Dict[str, Any] = {}  # default (empty) keywords

    def _updated_keywords(self, opts):
        kw_ = self.__kw.copy()
        kw_.update(opts)
        return kw_

    def __call__(self, admin=False, timestamps=False, **irods_kw_opt):
        if admin:
            irods_kw_opt.update([(kw.ADMIN_KW, "")])
        new_self = copy.copy(self)
        new_self._use_ts = timestamps
        new_self.__kw = irods_kw_opt
        return new_self

    @staticmethod
    def _model_class_to_resource_type(model_cls):
        return {
            DataObject: "d",
            Collection: "C",
            Resource: "R",
            User: "u",
        }[model_cls]

    @staticmethod
    def _model_class_to_resource_description(model_cls):
        return {
            DataObject: "data_object",
            Collection: "collection",
            Resource: "resource",
            User: "user",
        }[model_cls]

    def get(self, model_cls, path):
        resource_type = self._model_class_to_resource_type(model_cls)
        model = {
            "d": DataObjectMeta,
            "C": CollectionMeta,
            "R": ResourceMeta,
            "u": UserMeta,
        }[resource_type]
        conditions = {
            "d": [Collection.name == dirname(path), DataObject.name == basename(path)],
            "C": [Collection.name == path],
            "R": [Resource.name == path],
            "u": [User.name == path],
        }[resource_type]

        columns = (model.id, model.name, model.value, model.units)
        if self.use_timestamps:
            columns += (model.create_time, model.modify_time)
        results = self.sess.query(*columns).filter(*conditions)._all()

        def meta_opts(row):
            opts = {"avu_id": row[model.id]}
            if self.use_timestamps:
                opts.update(
                    create_time=row[model.create_time],
                    modify_time=row[model.modify_time],
                )
            return opts

        return [
            iRODSMeta(
                row[model.name], row[model.value], row[model.units], **meta_opts(row)
            )
            for row in results
        ]

    def add(self, model_cls, path, meta, **opts):

        resource_type = self._model_class_to_resource_type(model_cls)
        message_body = MetadataRequest(
            "add",
            "-" + resource_type,
            path,
            meta.name,
            meta.value,
            meta.units,
            **self._updated_keywords(opts)
        )
        request = iRODSMessage(
            "RODS_API_REQ", msg=message_body, int_info=api_number["MOD_AVU_METADATA_AN"]
        )
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)

    def remove(self, model_cls, path, meta, **opts):
        resource_type = self._model_class_to_resource_type(model_cls)
        message_body = MetadataRequest(
            "rm",
            "-" + resource_type,
            path,
            meta.name,
            meta.value,
            meta.units,
            **self._updated_keywords(opts)
        )
        request = iRODSMessage(
            "RODS_API_REQ", msg=message_body, int_info=api_number["MOD_AVU_METADATA_AN"]
        )
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)

    def copy(self, src_model_cls, dest_model_cls, src, dest, **opts):
        src_resource_type = self._model_class_to_resource_type(src_model_cls)
        dest_resource_type = self._model_class_to_resource_type(dest_model_cls)
        message_body = MetadataRequest(
            "cp",
            "-" + src_resource_type,
            "-" + dest_resource_type,
            src,
            dest,
            **self._updated_keywords(opts)
        )
        request = iRODSMessage(
            "RODS_API_REQ", msg=message_body, int_info=api_number["MOD_AVU_METADATA_AN"]
        )

        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)

    def set(self, model_cls, path, meta, **opts):
        resource_type = self._model_class_to_resource_type(model_cls)
        message_body = MetadataRequest(
            "set",
            "-" + resource_type,
            path,
            meta.name,
            meta.value,
            meta.units,
            **self._updated_keywords(opts)
        )
        request = iRODSMessage(
            "RODS_API_REQ", msg=message_body, int_info=api_number["MOD_AVU_METADATA_AN"]
        )
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)

    @staticmethod
    def _avu_operation_to_dict(op):
        opJSON = {
            "operation": op.operation,
            "attribute": op.avu.name,
            "value": op.avu.value,
        }
        if op.avu.units not in ("", None):
            opJSON["units"] = op.avu.units
        return opJSON

    def apply_atomic_operations(self, model_cls, path, *avu_ops):
        if not all(isinstance(op, AVUOperation) for op in avu_ops):
            raise InvalidAtomicAVURequest(
                "avu_ops must contain 1 or more AVUOperations"
            )
        request = {
            "admin_mode": True if kw.ADMIN_KW in self.__kw.keys() else False,
            "entity_name": path,
            "entity_type": self._model_class_to_resource_description(model_cls),
            "operations": [self._avu_operation_to_dict(op) for op in avu_ops],
        }
        self._call_atomic_metadata_api(request)

    def _call_atomic_metadata_api(self, request_text):
        with self.sess.pool.get_connection() as conn:
            request_msg = iRODSMessage(
                "RODS_API_REQ",
                JSON_Message(request_text, conn.server_version),
                int_info=api_number["ATOMIC_APPLY_METADATA_OPERATIONS_APN"],
            )
            conn.send(request_msg)
            response = conn.recv()
        response_msg = response.get_json_encoded_struct()
        logger.debug("in atomic_metadata, server responded with: %r", response_msg)
