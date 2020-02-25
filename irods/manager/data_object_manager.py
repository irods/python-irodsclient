from __future__ import absolute_import
import os
import io
import socket
import ssl
import struct
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import M2Crypto

from irods.models import DataObject
from irods.manager import Manager
from irods.message import (
    iRODSMessage, FileOpenRequest, ObjCopyRequest, StringStringMap, DataObjInfo, ModDataObjMeta, PortalOprResponse, OprComplete)
import irods.exception as ex
from irods.api_number import api_number
from irods.data_object import (
    iRODSDataObject, iRODSDataObjectFileRaw, chunks, irods_dirname, irods_basename)
from irods import DEFAULT_CONNECTION_TIMEOUT
import irods.keywords as kw


class LockCounter:
    def __init__(self, value=0):
        self.lock = threading.Lock()
        self.__value = value

    def __get_value(self):
        return self.__value

    def __set_value(self, new_value):
        with self.lock:
            self.__value = new_value
            return self.__value

    value = property(__get_value, __set_value)

    def __add(self, add):
        with self.lock:
            self.__value += add
            return self.__value

    def incr(self, increment=1):
        return self.__add(increment)

    def decr(self, decrement=1):
        return self.__add(- decrement)

def connect_to_portal(host, port, cookie,
                      timeout=DEFAULT_CONNECTION_TIMEOUT):
    address = (host, port)
    try:
        s = socket.create_connection(address, timeout)
    except socket.error:
        raise ex.NetworkException(
            "Could not connect to specified host and port: " +
            "{}:{}".format(*address))

    fmt = '!i'
    sent = s.send(struct.pack(fmt, cookie))

    if sent != struct.calcsize(fmt):
        s.close()
        raise ex.NetworkException(
            "SYS_PORT_COOKIE_ERR: {}:{}".format(*address))

    return s

def recv_xfer_header(sock):
    # typedef struct TransferHeader { int oprType; int flags;
    # rodsLong_t offset; rodsLong_t length; } transferHeader_t;

    fmt = '!iiqq'
    size = struct.calcsize(fmt)
    buf = bytearray(b'\0' * size)
    recv_size = sock.recv_into(buf, size)
    if recv_size != size:
        raise ex.SYS_COPY_LEN_ERR

    u = struct.unpack(fmt, buf)
    return u

class Encryption:
    def __init__(self, connection):
        self.algorithm = connection.account.encryption_algorithm.lower().replace('-', '_')
        self.key = connection.shared_secret
        self.key_size = connection.account.encryption_key_size

        self.ifmt = 'i'
        self.isize = struct.calcsize(self.ifmt)
        self.ibuf = bytearray(b'\0' * self.isize)

    def recv_int(self, sock):
        recv_size = sock.recv_into(self.ibuf, self.isize)

        if recv_size != self.isize:
            raise ex.SYS_COPY_LEN_ERR

        u = struct.unpack(self.ifmt, self.ibuf)
        return u[0]

    def send_int(self, sock, i):
        struct.pack_into(self.ifmt, self.ibuf, 0, i)

        sock.sendall(self.ibuf)

    def generate_key(self):
        return os.urandom(self.key_size)

    def __xxcrypt(self, iv, buf, op):
        cipher = M2Crypto.EVP.Cipher(alg=self.algorithm, key=self.key,
                                     iv=iv, op=op)
        return cipher.update(buf) + cipher.final()

    def decrypt(self, buf):
        iv = buf[0:self.key_size]
        text = buf[self.key_size:]
        try:
            return self.__xxcrypt(iv, text, op=0)
        except TypeError as e:
            # Python 2 doesn't seem to know that memoryview on bytearray
            # are bytelike objects...
            return self.__xxcrypt(bytearray(iv), bytearray(text), op=0)

    def encrypt(self, iv, buf):
        return iv + self.__xxcrypt(iv, buf, op=1)

class DataObjectManager(Manager):

    READ_BUFFER_SIZE = 1024 * io.DEFAULT_BUFFER_SIZE
    WRITE_BUFFER_SIZE = 1024 * io.DEFAULT_BUFFER_SIZE

    # Data object open flags (independent of client os)
    O_RDONLY = 0
    O_WRONLY = 1
    O_RDWR = 2
    O_APPEND = 1024
    O_CREAT = 64
    O_EXCL = 128
    O_TRUNC = 512

    # lib/api/include/dataObjInpOut.h
    DONE_OPR = 9999

    def _download(self, obj, local_path, **options):
        if os.path.isdir(local_path):
            file = os.path.join(local_path, irods_basename(obj))
        else:
            file = local_path

        # Check for force flag if file exists
        if os.path.exists(file) and kw.FORCE_FLAG_KW not in options:
            raise ex.OVERWRITE_WITHOUT_FORCE_FLAG

        with open(file, 'wb') as f, self.open(obj, 'r', **options) as o:
            for chunk in chunks(o, self.READ_BUFFER_SIZE):
                f.write(chunk)


    def get(self, path, file=None, **options):
        parent = self.sess.collections.get(irods_dirname(path))

        # TODO: optimize
        if file:
            self._download(path, file, **options)

        query = self.sess.query(DataObject)\
            .filter(DataObject.name == irods_basename(path))\
            .filter(DataObject.collection_id == parent.id)\
            .add_keyword(kw.ZONE_KW, path.split('/')[1])

        results = query.all() # get up to max_rows replicas
        if len(results) <= 0:
            raise ex.DataObjectDoesNotExist()
        return iRODSDataObject(self, parent, results)

    def download_parallel(self, irods_path, local_path, executor=None,
                          progress_cb=None, **options):

        progress_cb = progress_cb or (lambda l, i, c: True)

        def recv_task(host, port, cookie, local_path, conn, task_count):
            sock = connect_to_portal(host, port, cookie)
            try:
                with open(local_path, 'r+b') as lf:
                    buf = memoryview(bytearray(self.READ_BUFFER_SIZE))
                    if use_encryption:
                        crypt = Encryption(conn)

                    while True:
                        opr, flags, offset, size = recv_xfer_header(sock)
                        if opr == self.DONE_OPR:
                            break

                        lf.seek(offset)

                        while size > 0:
                            if task_count.value < 0:
                                return

                            to_read = min(size, self.READ_BUFFER_SIZE)

                            if use_encryption:
                                to_read = crypt.recv_int(sock)

                            all_read = 0
                            while all_read < to_read:
                                current = buf[all_read:]
                                read_size = sock.recv_into(current,
                                                           to_read - all_read)
                                all_read += read_size

                            plaintext = buf[0:all_read]

                            if use_encryption:
                                plaintext = crypt.decrypt(plaintext)
                                all_read = len(plaintext)

                            lf.write(plaintext)
                            size -= all_read

                            if not progress_cb(local_path, irods_path,
                                               all_read):
                                task_count.value = -1
                                conn.release()
            finally:
                sock.close()

            if task_count.decr() == 0:
                # last task has to complete iRODS operation
                message = iRODSMessage('RODS_API_REQ',
                                       OprComplete(myInt=desc),
                                       int_info=api_number['OPR_COMPLETE_AN'])

                conn.send(message)
                resp = conn.recv()
                conn.release()

        def write_from_response(irods_path, local_path, response, conn,
                                progress_cb):
            try:
                with open(local_path, 'wb') as lf:
                    lf.write(response.bs)
            finally:
                conn.release()
                progress_cb(local_path, irods_path, len(response.bs))

            return []

        # Check for force flag if local file exists
        if os.path.exists(local_path) and kw.FORCE_FLAG_KW not in options:
            raise ex.OVERWRITE_WITHOUT_FORCE_FLAG

        response, message, conn = self._open_request(irods_path,
                                                     'DATA_OBJ_GET_AN',
                                                     'r', 0, **options)

        use_encryption = conn.shared_secret is not None

        desc = message.l1descInx

        if desc <= 2:
            # file contents are directly embeded in catalog response

            if executor is not None:
                return [executor.submit(write_from_response, irods_path,
                                        local_path, response, conn,
                                        progress_cb)]

            write_from_response(local_path, response, conn)
            return []

        futs = []

        nt = message.numThreads
        if nt <= 0:
            nt = 1

        host = message.PortList_PI.hostAddr
        port = message.PortList_PI.portNum
        cookie = message.PortList_PI.cookie

        task_count = LockCounter(nt)

        join = False
        if executor is None:
            # handle parallel transfer with own executor
            executor = ThreadPoolExecutor(max_workers=nt)
            join = True

        with open(local_path, 'w') as lf:
            # create local file
            pass

        for i in range(nt):
            fut = executor.submit(recv_task, host, port, cookie,
                                  local_path, conn, task_count)

            futs.append(fut)

        if join:
            executor.shutdown()
            exceptions = []
            for f in futs:
                e=f.exception()
                if e is not None:
                    exceptions.append(e)
            if len(exceptions) > 0:
                msgs = ['%s%s' % (type(e).__name__, str(e)) for e in exceptions]
                raise Exception(', '.join(msgs))

        return futs

    def put(self, file, irods_path, return_data_object=False, **options):
        if irods_path.endswith('/'):
            obj = irods_path + os.path.basename(file)
        else:
            obj = irods_path

        # Set operation type to trigger acPostProcForPut
        if kw.OPR_TYPE_KW not in options:
            options[kw.OPR_TYPE_KW] = 1 # PUT_OPR

        with self.open(obj, 'w', **options) as o:
            self._put_opened_file(file, obj, o, **options)

        if kw.ALL_KW in options:
            options[kw.UPDATE_REPL_KW] = ''
            self.replicate(obj, **options)

        if return_data_object:
            return self.get(obj)


    def _put_opened_file(self, local_path, irods_path, obj, **options):
        with open(local_path, 'rb') as f:
            for chunk in chunks(f, self.WRITE_BUFFER_SIZE):
                obj.write(chunk)

    def put_parallel(self, local_path, irods_path, executor=None,
                     progress_cb=None, **options):

        progress_cb = progress_cb or (lambda l, i, c: True)

        def send_task(host, port, cookie, local_path, conn, task_count):
            sock = connect_to_portal(host, port, cookie)
            try:
                with open(local_path, 'rb') as lf:
                    if use_encryption:
                        crypt = Encryption(conn)

                    while True:
                        opr, flags, offset, size = recv_xfer_header(sock)

                        if opr == self.DONE_OPR:
                            break

                        lf.seek(offset)

                        if use_encryption:
                            iv = crypt.generate_key()

                        while size > 0:
                            if task_count.value < 0:
                                return
                            to_read = min(size, self.WRITE_BUFFER_SIZE)

                            buf = lf.read(to_read)
                            read_size = len(buf)

                            new_size = read_size
                            if use_encryption:
                                buf = crypt.encrypt(iv, buf)
                                new_size = len(buf)
                                crypt.send_int(sock, new_size)

                            sock.sendall(buf)

                            size -= read_size

                            if not progress_cb(local_path, irods_path,
                                               read_size):
                                task_count.value = -1
            finally:
                sock.close()

            if task_count.decr() == 0:
                # last task has to complete iRODS operation
                message = iRODSMessage('RODS_API_REQ',
                                       OprComplete(myInt=desc),
                                       int_info=api_number['OPR_COMPLETE_AN'])

                conn.send(message)
                resp = conn.recv()
                conn.release()

                replicate()

        def send_task_cb(fut):
            if fut.exception() is not None:
                # exception occurred in send_task. Mark other tasks for exit
                task_count.value = -1

        def send_to_catalog(conn, local_path, irods_path, desc, **options):
            with io.BufferedRandom(iRODSDataObjectFileRaw(conn,
                                   desc, **options)) as o:
                self._put_opened_file(local_path, irods_path, o,
                                      **options)
            replicate()

        def replicate():
            if kw.ALL_KW in options:
                options[kw.UPDATE_REPL_KW] = ''
                self.replicate(irods_path, **options)

        local_size = os.lstat(local_path).st_size

        # Set operation type to trigger acPostProcForPut
        if kw.OPR_TYPE_KW not in options:
            options[kw.OPR_TYPE_KW] = 1 # PUT_OPR

        # for now, can't handle ssl multithreaded operation
        with self.sess.pool.get_connection() as conn:
            use_encryption = isinstance(conn.socket, ssl.SSLSocket)

        response, message, conn = self._open_request(irods_path,
                                                     'DATA_OBJ_PUT_AN',
                                                     'w', local_size,
                                                     **options)
        desc = message.l1descInx
        nt = message.numThreads
        if nt <= 0:
            nt = 1

        futs = []
        join = False

        if executor is None:
            if nt <= 1:
                # sequential put
                send_to_catalog(conn, local_path, irods_path, desc,
                                **options)
                return []

            # handle parallel transfer with own executor
            executor = ThreadPoolExecutor(max_workers=nt)
            join = True

        if nt <= 1:
            fut = executor.submit(send_to_catalog, conn, local_path,
                                  irods_path, desc, **options)
            futs.append(fut)
        else:
            host = message.PortList_PI.hostAddr
            port = message.PortList_PI.portNum
            cookie = message.PortList_PI.cookie

            task_count = LockCounter(nt)

            for i in range(nt):
                fut = executor.submit(send_task, host, port, cookie,
                                      local_path, conn, task_count)
                fut.add_done_callback(send_task_cb)

                futs.append(fut)

        if join:
            executor.shutdown()
            exceptions = []
            for f in futs:
                e=f.exception()
                if e is not None:
                    exceptions.append(e)
            if len(exceptions) > 0:
                msgs = ['%s%s' % (type(e).__name__, str(e)) for e in exceptions]
                raise Exception(', '.join(msgs))

        return futs

    def create(self, path, resource=None, **options):
        options[kw.DATA_TYPE_KW] = 'generic'

        if resource:
            options[kw.DEST_RESC_NAME_KW] = resource
        else:
            # Use client-side default resource if available
            try:
                options[kw.DEST_RESC_NAME_KW] = self.sess.default_resource
            except AttributeError:
                pass

        message_body = FileOpenRequest(
            objPath=path,
            createMode=0o644,
            openFlags=0,
            offset=0,
            dataSize=-1,
            numThreads=self.sess.numThreads,
            oprType=0,
            KeyValPair_PI=StringStringMap(options),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_CREATE_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
            desc = response.int_info
            conn.close_file(desc)

        return self.get(path)


    def _open_request(self, path, an_name, mode, size, **options):
        if kw.DEST_RESC_NAME_KW not in options:
            # Use client-side default resource if available
            try:
                options[kw.DEST_RESC_NAME_KW] = self.sess.default_resource
            except AttributeError:
                pass

        try:
            oprType = options[kw.OPR_TYPE_KW]
        except KeyError:
            oprType = 0

        flags, seek_to_end = {
            'r': (self.O_RDONLY, False),
            'r+': (self.O_RDWR, False),
            'w': (self.O_WRONLY | self.O_CREAT | self.O_TRUNC, False),
            'w+': (self.O_RDWR | self.O_CREAT | self.O_TRUNC, False),
            'a': (self.O_WRONLY | self.O_CREAT, True),
            'a+': (self.O_RDWR | self.O_CREAT, True),
        }[mode]
        # TODO: Use seek_to_end

        message_body = FileOpenRequest(
            objPath=path,
            createMode=0,
            openFlags=flags,
            offset=0,
            dataSize=size,
            numThreads=self.sess.numThreads,
            oprType=oprType,
            KeyValPair_PI=StringStringMap(options),
        )

        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number[an_name])

        conn = self.sess.pool.get_connection()
        conn.send(message)
        resp = conn.recv()

        return resp, resp.get_main_message(PortalOprResponse), conn

    def open(self, path, mode, **options):
        if kw.DEST_RESC_NAME_KW not in options:
            # Use client-side default resource if available
            try:
                options[kw.DEST_RESC_NAME_KW] = self.sess.default_resource
            except AttributeError:
                pass

        flags, seek_to_end = {
            'r': (self.O_RDONLY, False),
            'r+': (self.O_RDWR, False),
            'w': (self.O_WRONLY | self.O_CREAT | self.O_TRUNC, False),
            'w+': (self.O_RDWR | self.O_CREAT | self.O_TRUNC, False),
            'a': (self.O_WRONLY | self.O_CREAT, True),
            'a+': (self.O_RDWR | self.O_CREAT, True),
        }[mode]
        # TODO: Use seek_to_end

        try:
            oprType = options[kw.OPR_TYPE_KW]
        except KeyError:
            oprType = 0

        message_body = FileOpenRequest(
            objPath=path,
            createMode=0,
            openFlags=flags,
            offset=0,
            dataSize=-1,
            numThreads=self.sess.numThreads,
            oprType=oprType,
            KeyValPair_PI=StringStringMap(options),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_OPEN_AN'])

        conn = self.sess.pool.get_connection()
        conn.send(message)
        desc = conn.recv().int_info

        return io.BufferedRandom(iRODSDataObjectFileRaw(conn, desc, **options))


    def unlink(self, path, force=False, **options):
        if force:
            options[kw.FORCE_FLAG_KW] = ''

        try:
            oprType = options[kw.OPR_TYPE_KW]
        except KeyError:
            oprType = 0

        message_body = FileOpenRequest(
            objPath=path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=-1,
            numThreads=self.sess.numThreads,
            oprType=oprType,
            KeyValPair_PI=StringStringMap(options),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_UNLINK_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()


    def unregister(self, path, **options):
        # https://github.com/irods/irods/blob/4.2.1/lib/api/include/dataObjInpOut.h#L190
        options[kw.OPR_TYPE_KW] = 26

        self.unlink(path, **options)


    def exists(self, path):
        try:
            self.get(path)
        except ex.DoesNotExist:
            return False
        return True


    def move(self, src_path, dest_path):
        # check if dest is a collection
        # if so append filename to it
        if self.sess.collections.exists(dest_path):
            filename = src_path.rsplit('/', 1)[1]
            target_path = dest_path + '/' + filename
        else:
            target_path = dest_path

        src = FileOpenRequest(
            objPath=src_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=self.sess.numThreads,
            oprType=11,   # RENAME_DATA_OBJ
            KeyValPair_PI=StringStringMap(),
        )
        dest = FileOpenRequest(
            objPath=target_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=self.sess.numThreads,
            oprType=11,   # RENAME_DATA_OBJ
            KeyValPair_PI=StringStringMap(),
        )
        message_body = ObjCopyRequest(
            srcDataObjInp_PI=src,
            destDataObjInp_PI=dest
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_RENAME_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()


    def copy(self, src_path, dest_path, **options):
        # check if dest is a collection
        # if so append filename to it
        if self.sess.collections.exists(dest_path):
            filename = src_path.rsplit('/', 1)[1]
            target_path = dest_path + '/' + filename
        else:
            target_path = dest_path

        src = FileOpenRequest(
            objPath=src_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=self.sess.numThreads,
            oprType=10,   # COPY_SRC
            KeyValPair_PI=StringStringMap(),
        )
        dest = FileOpenRequest(
            objPath=target_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=self.sess.numThreads,
            oprType=9,   # COPY_DEST
            KeyValPair_PI=StringStringMap(options),
        )
        message_body = ObjCopyRequest(
            srcDataObjInp_PI=src,
            destDataObjInp_PI=dest
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_COPY_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()


    def truncate(self, path, size, **options):
        message_body = FileOpenRequest(
            objPath=path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=size,
            numThreads=self.sess.numThreads,
            oprType=0,
            KeyValPair_PI=StringStringMap(options),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_TRUNCATE_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()


    def replicate(self, path, resource=None, **options):
        if resource:
            options[kw.DEST_RESC_NAME_KW] = resource

        message_body = FileOpenRequest(
            objPath=path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=-1,
            numThreads=self.sess.numThreads,
            oprType=6,
            KeyValPair_PI=StringStringMap(options),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_REPL_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()


    def register(self, file_path, obj_path, **options):
        options[kw.FILE_PATH_KW] = file_path

        message_body = FileOpenRequest(
            objPath=obj_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=self.sess.numThreads,
            oprType=0,
            KeyValPair_PI=StringStringMap(options),
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['PHY_PATH_REG_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()

    def modDataObjMeta(self, data_obj_info, meta_dict, **options):
        if "rescHier" not in data_obj_info and "rescName" not in data_obj_info and "replNum" not in data_obj_info:
            meta_dict["all"] = ""

        message_body = ModDataObjMeta(
            dataObjInfo=DataObjInfo(
                objPath=data_obj_info["objPath"],
                rescName=data_obj_info.get("rescName", ""),
                rescHier=data_obj_info.get("rescHier", ""),
                dataType="",
                dataSize=0,
                chksum="",
                version="",
                filePath="",
                dataOwnerName="",
                dataOwnerZone="",
                replNum=data_obj_info.get("replNum", 0),
                replStatus=0,
                statusString="",
                dataId=0,
                collId=0,
                dataMapId=0,
                flags=0,
                dataComments="",
                dataMode="",
                dataExpiry="",
                dataCreate="",
                dataModify="",
                dataAccess="",
                dataAccessInx=0,
                writeFlag=0,
                destRescName="",
                backupRescName="",
                subPath="",
                specColl=0,
                regUid=0,
                otherFlags=0,
                KeyValPair_PI=StringStringMap(options),
                in_pdmo="",
                next=0,
                rescId=0
                ),
            regParam=StringStringMap(meta_dict)
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['MOD_DATA_OBJ_META_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
