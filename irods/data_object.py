from __future__ import absolute_import
import io
import sys
import logging
import six
import os
import ast

from irods.models import DataObject
from irods.meta import iRODSMetaCollection
import irods.keywords as kw
from irods.api_number import api_number
from irods.message import (JSON_Message, iRODSMessage)

logger = logging.getLogger(__name__)

IRODS_SERVER_WITH_CLOSE_REPLICA_API = (4,2,9)

def chunks(f, chunksize=io.DEFAULT_BUFFER_SIZE):
    return iter(lambda: f.read(chunksize), b'')

def irods_dirname(path):
    return path.rsplit('/', 1)[0]

def irods_basename(path):
    return path.rsplit('/', 1)[1]


class iRODSReplica(object):

    def __init__(self, number, status, resource_name, path, resc_hier, **kwargs):
        self.number = number
        self.status = status
        self.resource_name = resource_name
        self.path = path
        self.resc_hier = resc_hier
        for key, value in kwargs.items():
            setattr(self, key, value)


    def __repr__(self):
        return "<{}.{} {}>".format(
            self.__class__.__module__,
            self.__class__.__name__,
            self.resource_name
        )


class iRODSDataObject(object):

    def __init__(self, manager, parent=None, results=None):
        self.manager = manager
        if parent and results:
            self.collection = parent
            for attr, value in six.iteritems(DataObject.__dict__):
                if not attr.startswith('_'):
                    try:
                        setattr(self, attr, results[0][value])
                    except KeyError:
                        # backward compatibility with older schema versions
                        pass
            self.path = self.collection.path + '/' + self.name
            replicas = sorted(
                results, key=lambda r: r[DataObject.replica_number])
            self.replicas = [iRODSReplica(
                r[DataObject.replica_number],
                r[DataObject.replica_status],
                r[DataObject.resource_name],
                r[DataObject.path],
                r[DataObject.resc_hier],
                checksum=r[DataObject.checksum],
                size=r[DataObject.size]
            ) for r in replicas]
        self._meta = None




    def __repr__(self):
        return "<iRODSDataObject {id} {name}>".format(**vars(self))

    @property
    def metadata(self):
        if not self._meta:
            self._meta = iRODSMetaCollection(
                self.manager.sess.metadata, DataObject, self.path)
        return self._meta

    def open(self, mode='r', finalize_on_close = True, **options):
        return self.manager.open(self.path, mode, finalize_on_close = finalize_on_close, **options)

    def chksum(self, **options):
        """
        See: https://github.com/irods/irods/blob/4-2-stable/lib/api/include/dataObjChksum.h
        for a list of applicable irods.keywords options.

        NB options dict may also include a default-constructed RErrorStack object under the key r_error.
        If passed, this object can receive a list of warnings, one for each existing replica lacking a
        checksum.  (Relevant only in combination with VERIFY_CHKSUM_KW).
        """
        return self.manager.chksum(self.path, **options)

    def unlink(self, force=False, **options):
        self.manager.unlink(self.path, force, **options)

    def unregister(self, **options):
        self.manager.unregister(self.path, **options)

    def truncate(self, size):
        self.manager.truncate(self.path, size)

    def replicate(self, resource=None, **options):
        if resource:
            options[kw.DEST_RESC_NAME_KW] = resource
        self.manager.replicate(self.path, **options)


class iRODSDataObjectFileRaw(io.RawIOBase):

    """The raw object supporting file-like operations (read/write/seek) for the
       iRODSDataObject."""

    def __init__(self, conn, descriptor, finalize_on_close = True, **options):
        """
        Constructor needs a connection and an iRODS data object descriptor. If the
        finalize_on_close flag evaluates False, close() will invoke the REPLICA_CLOSE
        API instead of closing and finalizing the object (useful for parallel
        transfers using multiple threads).
        """
        super(iRODSDataObjectFileRaw,self).__init__()
        self.conn = conn
        self.desc = descriptor
        self.options = options
        self.finalize_on_close = finalize_on_close

    def replica_access_info(self):
        message_body = JSON_Message( {'fd': self.desc},
                                     server_version = self.conn.server_version )
        message = iRODSMessage('RODS_API_REQ', msg = message_body,
                               int_info=api_number['GET_FILE_DESCRIPTOR_INFO_APN'])
        self.conn.send(message)
        result = None
        try:
            result = self.conn.recv()
        except Exception as e:
            logger.warning('''Couldn't receive or process response to GET_FILE_DESCRIPTOR_INFO_APN -- '''
                           '''caught: %r''',e)
            raise
        dobj_info = result.get_json_encoded_struct()
        replica_token = dobj_info.get("replica_token","")
        resc_hier = ( dobj_info.get("data_object_info") or {} ).get("resource_hierarchy","")
        return (replica_token, resc_hier)

    def _close_replica(self):
        server_version = ast.literal_eval(os.environ.get('IRODS_VERSION_OVERRIDE', '()' ))
        if (server_version or self.conn.server_version) < IRODS_SERVER_WITH_CLOSE_REPLICA_API: return False
        message_body = JSON_Message( { "fd": self.desc,
                                       "send_notification": False,
                                       "update_size": False,
                                       "update_status": False,
                                       "compute_checksum": False },
                                     server_version = self.conn.server_version )
        self.conn.send( iRODSMessage('RODS_API_REQ', msg = message_body,
                                     int_info=api_number['REPLICA_CLOSE_APN']) )
        try:
            self.conn.recv().int_info
        except Exception:
            logger.warning ('** ERROR on closing replica **')
            raise
        return True

    def close(self):
        if self.finalize_on_close or not self._close_replica():
            self.conn.close_file(self.desc, **self.options)
        self.conn.release()
        super(iRODSDataObjectFileRaw, self).close()
        return None

    def seek(self, offset, whence=0):
        return self.conn.seek_file(self.desc, offset, whence)

    def readinto(self, b):
        contents = self.conn.read_file(self.desc, buffer=b)
        if contents is None:
            return 0

        return len(contents)

    def write(self, b):
        if isinstance(b, memoryview):
            return self.conn.write_file(self.desc, b.tobytes())

        return self.conn.write_file(self.desc, b)

    def readable(self):
        return True

    def writable(self):
        return True

    def seekable(self):
        return True
