import ast
import collections
import io
import json
import logging
import os
import weakref
from typing import Any, List, Type
from irods.models import DataObject, Collection
from irods.manager import Manager
from irods.manager._internal import _api_impl, _logical_path
from irods.message import (
    iRODSMessage,
    FileOpenRequest,
    ObjCopyRequest,
    StringStringMap,
    DataObjInfo_for_session,
    ModDataObjMeta_for_session,
    DataObjChksumRequest,
    DataObjChksumResponse,
    RErrorStack,
    STR_PI,
)
import irods.exception as ex
from irods.api_number import api_number
from irods.collection import iRODSCollection
from irods.data_object import (
    iRODSDataObject,
    iRODSDataObjectFileRaw,
    chunks,
    irods_dirname,
    irods_basename,
)
import irods.client_configuration as client_config
import irods.keywords as kw
import irods.parallel as parallel
from irods.parallel import deferred_call


logger = logging.getLogger(__name__)

_update_types: List[Type] = []
_update_functions: weakref.WeakKeyDictionary[Type, Any] = weakref.WeakKeyDictionary()


def register_update_instance(object_, updater):  # updater
    _update_functions[object_] = updater


def register_update_type(type_, factory_):
    """
    Create an entry corresponding to a type_ of instance to be allowed among updatables, with processing
    based on the factory_ callable.

    Parameters:
    type_ : a type of instance to be allowed in the updatables parameter.
    factory_ : a function accepting the instance passed in, and yielding an update callable.
               If None, then remove the type from the list.
    """

    # Delete if already present in list
    z = tuple(zip(*_update_types))
    if z and type_ in z[0]:
        _update_types.pop(z[0].index(type_))
    # Rewrite the list
    #     - with the new item introduced at the start of the list but otherwise in the same order, and
    #     - preserving only pairs that do not contain 'None' as the second member.
    _update_types[:] = list(
        (k, v)
        for k, v in collections.OrderedDict([(type_, factory_)] + _update_types).items()
        if v is not None
    )


def unregister_update_type(type_):
    """
    Remove type_ from the listof recognized updatable types maintained by the PRC.
    """
    register_update_type(type_, None)


def do_progress_updates(updatables, n, logging_function=logger.warning):
    """
    Used internally by Python iRODS Client's data transfer routines (put, get) to iterate through updatables to be processed.
    This, in turn, should cause the underlying corresponding progress bars or indicators to be updated.
    """
    if not isinstance(updatables, (list, tuple)):
        updatables = [updatables]

    for object_ in updatables:
        # If an updatable is directly callable, we set that up to be called without further ado.
        if callable(object_):
            update_func = object_
        else:
            # If not, we search for a registered type that matches object_ and register (or look up if previously registered) a factory-produced updater for that instance.
            # Examine the unit tests for issue #574 in data_obj_test.py for factory examples.
            update_func = _update_functions.get(object_)
            if not update_func:
                # search based on type
                for class_, factory_ in _update_types:
                    if isinstance(object_, class_):
                        update_func = factory_(object_)
                        register_update_instance(object_, update_func)
                        break
                else:
                    logging_function(
                        "Could not derive an update function for: %r", object_
                    )
                    continue

        # Do the update.
        if update_func:
            update_func(n)


def call___del__if_exists(super_):
    """
    Utility method to call __del__ if it exists anywhere in superclasses' MRO (method
    resolution order).
    """
    next_finalizer_in_MRO = getattr(super_, "__del__", None)
    if next_finalizer_in_MRO:
        next_finalizer_in_MRO()


class ManagedBufferedRandom(io.BufferedRandom):

    def __init__(self, *a, **kwd):
        # Help ensure proper teardown sequence by storing a reference to the session,
        # if provided via keyword '_session'.
        self._iRODS_session = kwd.pop("_session", None)
        super(ManagedBufferedRandom, self).__init__(*a, **kwd)
        import irods.session

        with irods.session._fds_lock:
            irods.session._fds[self] = None

    def __del__(self):
        if not self.closed:
            self.close()
        call___del__if_exists(super(ManagedBufferedRandom, self))


MAXIMUM_SINGLE_THREADED_TRANSFER_SIZE = 32 * (1024**2)

DEFAULT_NUMBER_OF_THREADS = (
    0  # Defaults for reasonable number of threads -- optimized to be
)
# performant but allow no more worker threads than available CPUs.

DEFAULT_QUEUE_DEPTH = 32

logger = logging.getLogger(__name__)


class Server_Checksum_Warning(Exception):
    """Error from iRODS server indicating some replica checksums are missing or incorrect."""

    def __init__(self, json_response):
        """Initialize the exception object with a checksum field from the server response message."""
        super(Server_Checksum_Warning, self).__init__()
        self.response = json.loads(json_response)


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

    def should_parallelize_transfer(
        self,
        num_threads=0,
        obj_sz=1 + MAXIMUM_SINGLE_THREADED_TRANSFER_SIZE,
        server_version_hint=(),
        measured_obj_size=(),  ## output variable. If a list is provided, it shall
        # be truncated to contain one value, the presumed size of the
        # file or data object - if one is provided for `obj_sz'.  That size is
        # determined normally by stat'ing (using a seek-to-end operation) but
        # can be overridden using the DATA_SIZE_KW option.
        open_options=(),  # If this parameter is of type dict, set the DATA_SIZE_KW item from
        # the stat'ed size
    ):

        provided_data_size = dict(open_options).get(kw.DATA_SIZE_KW)
        # Allow an environment variable to override the detection of the server version.
        # Example: $ export IRODS_VERSION_OVERRIDE="4,2,9" ;  python -m irods.parallel ...
        server_version = (
            ast.literal_eval(os.environ.get("IRODS_VERSION_OVERRIDE", "()"))
            or server_version_hint
            or self.server_version
        )
        size = None
        try:
            if num_threads == 1 or (server_version < parallel.MINIMUM_SERVER_VERSION):
                return False
            if getattr(obj_sz, "seek", None):
                if provided_data_size is not None:
                    size = int(provided_data_size)
                else:
                    pos = obj_sz.tell()
                    size = obj_sz.seek(0, os.SEEK_END)
                    if not isinstance(size, int):
                        size = obj_sz.tell()
                    obj_sz.seek(pos, os.SEEK_SET)
                if isinstance(measured_obj_size, list):
                    measured_obj_size[:] = [size]
                return size > MAXIMUM_SINGLE_THREADED_TRANSFER_SIZE
            elif isinstance(obj_sz, int):
                return obj_sz > MAXIMUM_SINGLE_THREADED_TRANSFER_SIZE
            message = "obj_sz of {obj_sz!r} is neither an integer nor a seekable object".format(
                **locals()
            )
            raise RuntimeError(message)
        finally:
            if size is not None and isinstance(open_options, dict):
                open_options[kw.DATA_SIZE_KW] = size

    def _download(self, obj, local_path, num_threads, updatables=(), **options):
        """Transfer the contents of a data object to a local file.

        Called from get() when a local path is named.
        """
        if os.path.isdir(local_path):
            local_file = os.path.join(local_path, irods_basename(obj))
        else:
            local_file = local_path

        # Check for force flag if local_file exists
        if os.path.exists(local_file) and kw.FORCE_FLAG_KW not in options:
            raise ex.OVERWRITE_WITHOUT_FORCE_FLAG

        data_open_returned_values_ = {}
        with self.open(
            obj, "r", returned_values=data_open_returned_values_, **options
        ) as o:
            if self.should_parallelize_transfer(
                num_threads, o, open_options=options.items()
            ):
                if not self.parallel_get(
                    (obj, o),
                    local_file,
                    num_threads=num_threads,
                    target_resource_name=options.get(kw.RESC_NAME_KW, ""),
                    data_open_returned_values=data_open_returned_values_,
                    updatables=updatables,
                ):
                    raise RuntimeError("parallel get failed")
            else:
                with open(local_file, "wb") as f:
                    for chunk in chunks(o, self.READ_BUFFER_SIZE):
                        f.write(chunk)
                        do_progress_updates(updatables, len(chunk))

    def get(
        self,
        path,
        local_path=None,
        num_threads=DEFAULT_NUMBER_OF_THREADS,
        updatables=(),
        **options
    ):
        """
        Get a reference to the data object at the specified `path'.

        Only download the object if the local_path is a string (specifying
        a path in the local filesystem to use as a destination file).
        """
        parent = self.sess.collections.get(irods_dirname(path))

        # TODO: optimize
        if local_path:
            self._download(
                path,
                local_path,
                num_threads=num_threads,
                updatables=updatables,
                **options
            )

        query = (
            self.sess.query(DataObject)
            .filter(DataObject.name == irods_basename(path))
            .filter(DataObject.collection_id == parent.id)
            .add_keyword(kw.ZONE_KW, path.split("/")[1])
        )

        if self.sess.ticket__:
            query = query.filter(
                Collection.id != 0
            )  # a no-op, but necessary because CAT_SQL_ERR results if the ticket
            # is for a DataObject and we don't explicitly join to Collection

        results = query.all()  # get up to max_rows replicas
        if len(results) <= 0:
            raise ex.DataObjectDoesNotExist()
        return iRODSDataObject(self, parent, results)

    @staticmethod
    def _resolve_force_put_option(options, default_setting=None, true_value=""):
        """If 'default_setting' is True or the force flag is already set in 'options', leave (or put) the flag there,
        with the value set to the 'truth_value'.

        If the result of this resolves as False for the force flag in the 'options' dict, we then choose to remove the flag
        from `options`, since it is the flag's mere presence in the API call that achieves the forcing behavior.

        For the same reason, we also count string values (even empty ones) as unconditionally True, since that is convention
        for server APIs that use the FORCE_FLAG_KW.
        """

        force = options.setdefault(kw.FORCE_FLAG_KW, default_setting)
        if force or isinstance(force, str):
            options[kw.FORCE_FLAG_KW] = true_value
        else:
            del options[kw.FORCE_FLAG_KW]

    def put(
        self,
        local_path,
        irods_path,
        return_data_object=False,
        num_threads=DEFAULT_NUMBER_OF_THREADS,
        updatables=(),
        **options
    ):
        # Decide if a put option should be used and modify options accordingly.
        self._resolve_force_put_option(
            options, default_setting=client_config.data_objects.force_put_by_default
        )

        if self.sess.collections.exists(irods_path):
            obj = iRODSCollection.normalize_path(
                irods_path, os.path.basename(local_path)
            )
        else:
            obj = irods_path
            if kw.FORCE_FLAG_KW not in options and self.exists(obj):
                raise ex.OVERWRITE_WITHOUT_FORCE_FLAG
        options.pop(kw.FORCE_FLAG_KW, None)

        with open(local_path, "rb") as f:
            sizelist = []
            if self.should_parallelize_transfer(
                num_threads, f, measured_obj_size=sizelist, open_options=options
            ):
                o = deferred_call(self.open, (obj, "w"), options)
                f.close()
                if not self.parallel_put(
                    local_path,
                    (obj, o),
                    total_bytes=sizelist[0],
                    num_threads=num_threads,
                    target_resource_name=options.get(kw.RESC_NAME_KW, "")
                    or options.get(kw.DEST_RESC_NAME_KW, ""),
                    open_options=options,
                    updatables=updatables,
                ):
                    raise RuntimeError("parallel put failed")
            else:
                with self.open(obj, "w", **options) as o:
                    # Set operation type to trigger acPostProcForPut
                    if kw.OPR_TYPE_KW not in options:
                        options[kw.OPR_TYPE_KW] = 1  # PUT_OPR
                    for chunk in chunks(f, self.WRITE_BUFFER_SIZE):
                        o.write(chunk)
                        do_progress_updates(updatables, len(chunk))
        if kw.ALL_KW in options:
            repl_options = options.copy()
            repl_options[kw.UPDATE_REPL_KW] = ""
            # Leaving REG_CHKSUM_KW set would raise the error:
            # Requested to register checksum without verifying, but source replica has a checksum. This can result
            # in multiple replicas being marked good with different checksums, which is an inconsistency.
            del repl_options[kw.REG_CHKSUM_KW]
            self.replicate(obj, **repl_options)

        if return_data_object:
            return self.get(obj)

    def chksum(self, path, **options):
        """
        See: https://github.com/irods/irods/blob/4-2-stable/lib/api/include/dataObjChksum.h
        for a list of applicable irods.keywords options.
        """
        r_error_stack = options.pop("r_error", None)
        message_body = DataObjChksumRequest(path, **options)
        message = iRODSMessage(
            "RODS_API_REQ", msg=message_body, int_info=api_number["DATA_OBJ_CHKSUM_AN"]
        )
        checksum = ""
        msg_retn = []
        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            try:
                response = conn.recv(return_message=msg_retn)
            except ex.CHECK_VERIFICATION_RESULTS as exc:
                # We'll get a response in the client to help qualify or elaborate on the error thrown.
                if msg_retn:
                    response = msg_retn[0]
                logging.warning("Exception checksumming data object %r - %r", path, exc)
            if "response" in locals():
                try:
                    results = response.get_main_message(
                        DataObjChksumResponse, r_error=r_error_stack
                    )
                    checksum = results.myStr.strip()
                    if checksum[0] in (
                        "[",
                        "{",
                    ):  # in iRODS 4.2.11 and later, myStr is in JSON format.
                        exception = Server_Checksum_Warning(checksum)
                        if not r_error_stack:
                            r_error_stack.fill(exception.response)
                        raise exception
                except iRODSMessage.ResponseNotParseable:
                    # response.msg is None when VERIFY_CHKSUM_KW is used
                    pass
        return checksum

    def parallel_get(
        self,
        data_or_path_,
        file_,
        async_=False,
        num_threads=0,
        target_resource_name="",
        data_open_returned_values=None,
        progressQueue=False,
        updatables=(),
    ):
        """Call into the irods.parallel library for multi-1247 GET.

        Called from a session.data_objects.get(...) (via the _download method) on
        the condition that the data object is determined to be of appropriate size
        for parallel download.

        """
        return parallel.io_main(
            self.sess,
            data_or_path_,
            parallel.Oper.GET | (parallel.Oper.NONBLOCKING if async_ else 0),
            file_,
            num_threads=num_threads,
            target_resource_name=target_resource_name,
            data_open_returned_values=data_open_returned_values,
            queueLength=(DEFAULT_QUEUE_DEPTH if progressQueue else 0),
            updatables=updatables,
        )

    def parallel_put(
        self,
        file_,
        data_or_path_,
        async_=False,
        total_bytes=-1,
        num_threads=0,
        target_resource_name="",
        open_options={},
        updatables=(),
        progressQueue=False,
    ):
        """Call into the irods.parallel library for multi-1247 PUT.

        Called from a session.data_objects.put(...) on the condition that the
        data object is determined to be of appropriate size for parallel upload.

        """
        return parallel.io_main(
            self.sess,
            data_or_path_,
            parallel.Oper.PUT | (parallel.Oper.NONBLOCKING if async_ else 0),
            file_,
            num_threads=num_threads,
            total_bytes=total_bytes,
            target_resource_name=target_resource_name,
            open_options=open_options,
            queueLength=(DEFAULT_QUEUE_DEPTH if progressQueue else 0),
            updatables=updatables,
        )

    @staticmethod
    def _call_thru(c):
        return c() if callable(c) else c

    def create(
        self,
        path,
        resource=None,
        force=client_config.getter("data_objects", "force_create_by_default"),
        **options
    ):
        """
        Create a new data object with the given logical path.

        'resource', if provided, is the root node of a storage resource hierarchy where the object is preferentially to be created.
        'force', when False, raises an DataObjectExistsAtLogicalPath if there is already a data object at the logical path specified.
        """

        if not self._call_thru(force) and self.exists(path):
            raise ex.DataObjectExistsAtLogicalPath

        options = {**options, kw.DATA_TYPE_KW: "generic"}

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
        message = iRODSMessage(
            "RODS_API_REQ", msg=message_body, int_info=api_number["DATA_OBJ_CREATE_AN"]
        )

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
            desc = response.int_info
            conn.close_file(desc)

        return self.get(path)

    def open_with_FileRaw(self, *arg, **kw_options):
        holder = []
        handle = self.open(*arg, _raw_fd_holder=holder, **kw_options)
        return (handle, holder[-1])

    _RESC_flags_for_open = frozenset(
        (
            kw.RESC_NAME_KW,
            kw.DEST_RESC_NAME_KW,  # may be deprecated in the future
            kw.RESC_HIER_STR_KW,
        )
    )

    def open(
        self,
        path,
        mode,
        create=True,  # (Dis-)allow object creation.
        finalize_on_close=True,  # For PRC internal use.
        auto_close=client_config.getter(
            "data_objects", "auto_close"
        ),  # The default value will be a lambda returning the
        # global setting. Use True or False as an override.
        returned_values=None,  # Used to update session reference, for forging more conns to same host, in irods.parallel.io_main
        allow_redirect=client_config.getter("data_objects", "allow_redirect"),
        **options
    ):
        _raw_fd_holder = options.get("_raw_fd_holder", [])
        # If no keywords are used that would influence the server as to the choice of a storage resource,
        # then use the default resource in the client configuration.
        if self._RESC_flags_for_open.isdisjoint(options.keys()):
            # Use client-side default resource if available
            try:
                options[kw.DEST_RESC_NAME_KW] = self.sess.default_resource
            except AttributeError:
                pass
        createFlag = self.O_CREAT if create else 0
        flags, seek_to_end = {
            "r": (self.O_RDONLY, False),
            "r+": (self.O_RDWR, False),
            "w": (self.O_WRONLY | createFlag | self.O_TRUNC, False),
            "w+": (self.O_RDWR | createFlag | self.O_TRUNC, False),
            "a": (self.O_WRONLY | createFlag, True),
            "a+": (self.O_RDWR | createFlag, True),
        }[mode]
        # TODO: Use seek_to_end

        if not isinstance(returned_values, dict):
            returned_values = {}

        try:
            oprType = options[kw.OPR_TYPE_KW]
        except KeyError:
            oprType = 0

        dataSize_default = "0" if self.server_version < (4, 3, 1) else "-1"

        def make_FileOpenRequest(**extra_opts):
            options_ = dict(options) if extra_opts else options
            options_.update(extra_opts)
            return FileOpenRequest(
                objPath=path,
                createMode=0,
                openFlags=flags,
                offset=0,
                dataSize=int(options.get(kw.DATA_SIZE_KW, dataSize_default)),
                numThreads=self.sess.numThreads,
                oprType=oprType,
                KeyValPair_PI=StringStringMap(options_),
            )

        requested_hierarchy = options.get(kw.RESC_HIER_STR_KW, None)

        conn = self.sess.pool.get_connection()
        redirected_host = ""

        use_get_rescinfo_apis = False

        if callable(allow_redirect):
            allow_redirect = allow_redirect()

        if allow_redirect and conn.server_version >= (4, 3, 1):
            key = "CREATE" if mode[0] in ("w", "a") else "OPEN"
            message = iRODSMessage(
                "RODS_API_REQ",
                msg=make_FileOpenRequest(**{kw.GET_RESOURCE_INFO_OP_TYPE_KW: key}),
                int_info=api_number["GET_RESOURCE_INFO_FOR_OPERATION_AN"],
            )
            conn.send(message)
            response = conn.recv()
            msg = response.get_main_message(STR_PI)
            use_get_rescinfo_apis = True

            # Get the information needed for the redirect
            _ = json.loads(msg.myStr)
            redirected_host = _["host"]
            requested_hierarchy = _["resource_hierarchy"]

        target_zone = list(filter(None, path.split("/")))
        if target_zone:
            target_zone = target_zone[0]

        directed_sess = self.sess

        if redirected_host and use_get_rescinfo_apis:
            # Redirect only if the local zone is being targeted, and if the hostname is changed from the original.
            if target_zone == self.sess.zone and (self.sess.host != redirected_host):
                # This is the actual redirect.
                directed_sess = self.sess.clone(host=redirected_host)
                returned_values["session"] = directed_sess
                conn.release()
                conn = directed_sess.pool.get_connection()
                logger.debug("redirect_to_host = %s", redirected_host)

        # Restore RESC HIER for DATA_OBJ_OPEN call
        if requested_hierarchy is not None:
            options[kw.RESC_HIER_STR_KW] = requested_hierarchy
        message_body = make_FileOpenRequest()

        # Perform DATA_OBJ_OPEN call
        message = iRODSMessage(
            "RODS_API_REQ", msg=message_body, int_info=api_number["DATA_OBJ_OPEN_AN"]
        )
        conn.send(message)
        desc = conn.recv().int_info

        raw = iRODSDataObjectFileRaw(
            conn, desc, finalize_on_close=finalize_on_close, **options
        )
        raw.session = directed_sess

        (_raw_fd_holder).append(raw)

        if callable(auto_close):
            # Use case: auto_close has defaulted to the irods.configuration getter.
            # access entry in irods.configuration
            auto_close = auto_close()
        if auto_close:
            ret_value = ManagedBufferedRandom(raw, _session=self.sess)
        else:
            ret_value = io.BufferedRandom(raw)
        if "a" in mode:
            ret_value.seek(0, io.SEEK_END)
        return ret_value

    def replica_truncate(self, path, desired_size, **options):

        if self.sess.server_version == (4, 3, 2):
            message = "replica_truncate responses can fail to parse with iRODS 4.3.2 due to routine omission of the JSON response string, so this method is not supported for iRODS 4.3.2."
            raise ex.OperationNotSupported(message)
        else:
            required_server_version = (4, 3, 3)
            if self.sess.server_version < required_server_version:
                raise ex.NotImplementedInIRODSServer(
                    "replica_truncate", required_server_version
                )

        message_body = FileOpenRequest(
            objPath=path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=desired_size,
            numThreads=self.sess.numThreads,
            oprType=0,
            KeyValPair_PI=StringStringMap(options),
        )
        message = iRODSMessage(
            "RODS_API_REQ", msg=message_body, int_info=api_number["REPLICA_TRUNCATE_AN"]
        )

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
            msg = response.get_main_message(STR_PI)

        return json.loads(msg.myStr)

    def trim(self, path, **options):

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
        message = iRODSMessage(
            "RODS_API_REQ", msg=message_body, int_info=api_number["DATA_OBJ_TRIM_AN"]
        )

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()

    def unlink(self, path, force=False, **options):
        if force:
            options[kw.FORCE_FLAG_KW] = ""

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
        message = iRODSMessage(
            "RODS_API_REQ", msg=message_body, int_info=api_number["DATA_OBJ_UNLINK_AN"]
        )

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()

    def unregister(self, path, **options):
        # https://github.com/irods/irods/blob/4.2.1/lib/api/include/dataObjInpOut.h#L190
        options[kw.OPR_TYPE_KW] = 26  # UNREG_OPR: prevents deletion from disk.

        # If a replica is targeted, use trim API.
        if {kw.RESC_NAME_KW, kw.REPL_NUM_KW} & set(options.keys()):
            self.trim(path, **options)
        else:
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
            filename = src_path.rsplit("/", 1)[1]
            target_path = dest_path + "/" + filename
        else:
            target_path = dest_path

        src = FileOpenRequest(
            objPath=src_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=self.sess.numThreads,
            oprType=11,  # RENAME_DATA_OBJ
            KeyValPair_PI=StringStringMap(),
        )
        dest = FileOpenRequest(
            objPath=target_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=self.sess.numThreads,
            oprType=11,  # RENAME_DATA_OBJ
            KeyValPair_PI=StringStringMap(),
        )
        message_body = ObjCopyRequest(srcDataObjInp_PI=src, destDataObjInp_PI=dest)
        message = iRODSMessage(
            "RODS_API_REQ", msg=message_body, int_info=api_number["DATA_OBJ_RENAME_AN"]
        )

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()

    def copy(self, src_path, dest_path, **options):
        # check if dest is a collection
        # if so append filename to it
        if self.sess.collections.exists(dest_path):
            filename = src_path.rsplit("/", 1)[1]
            target_path = dest_path + "/" + filename
        else:
            target_path = dest_path

        src = FileOpenRequest(
            objPath=src_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=self.sess.numThreads,
            oprType=10,  # COPY_SRC
            KeyValPair_PI=StringStringMap(),
        )
        dest = FileOpenRequest(
            objPath=target_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=self.sess.numThreads,
            oprType=9,  # COPY_DEST
            KeyValPair_PI=StringStringMap(options),
        )
        message_body = ObjCopyRequest(srcDataObjInp_PI=src, destDataObjInp_PI=dest)
        message = iRODSMessage(
            "RODS_API_REQ", msg=message_body, int_info=api_number["DATA_OBJ_COPY_AN"]
        )

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
        message = iRODSMessage(
            "RODS_API_REQ",
            msg=message_body,
            int_info=api_number["DATA_OBJ_TRUNCATE_AN"],
        )

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()

    def replicate(self, path, resource=None, **options):
        if resource:
            options[kw.DEST_RESC_NAME_KW] = resource
        else:
            def_resc = getattr(self.sess, "default_resource", None)
            if def_resc:
                options[kw.DEF_RESC_NAME_KW] = def_resc

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
        message = iRODSMessage(
            "RODS_API_REQ", msg=message_body, int_info=api_number["DATA_OBJ_REPL_AN"]
        )

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
        message = iRODSMessage(
            "RODS_API_REQ", msg=message_body, int_info=api_number["PHY_PATH_REG_AN"]
        )

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()

    def modDataObjMeta(self, data_obj_info, meta_dict, **options):
        if (
            "rescHier" not in data_obj_info
            and "rescName" not in data_obj_info
            and "replNum" not in data_obj_info
        ):
            meta_dict["all"] = ""

        fields = dict(
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
            rescId=0,
        )

        DataObjInfo_class = DataObjInfo_for_session(self.sess)

        if 'dataAccessTime' in DataObjInfo_class.__dict__:
            fields["dataAccessTime"]=""

        message_body = ModDataObjMeta_for_session(self.sess)(
            dataObjInfo=DataObjInfo_class(**fields),
            regParam=StringStringMap(meta_dict),
        )

        message = iRODSMessage(
            "RODS_API_REQ",
            msg=message_body,
            int_info=api_number["MOD_DATA_OBJ_META_AN"],
        )

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()

    def touch(self, path, **options):
        """Change the mtime of a data object.

        A path argument that does not exist will be created as an empty data
        object, unless "no_create=True" is supplied.

        Parameters
        ----------
        path: string
            The absolute logical path of a data object.

        no_create: boolean, optional
            Instructs the system not to create a data object when it does not
            exist.

        replica_number: integer, optional
            The replica number of the replica to update. Replica numbers cannot
            be used to create data objects or additional replicas. Cannot be used
            with "leaf_resource_name".

        leaf_resource_name: string, optional
            The name of the leaf resource containing the replica to update. If
            the object identified by the "path" parameter does not exist and this
            parameter holds a valid resource, the data object will be created at
            the specified resource. Cannot be used with "replica_number" parameter.

        seconds_since_epoch: integer, optional
            The number of seconds since epoch representing the new mtime. Cannot
            be used with "reference" parameter.

        reference: string, optional
            Use the mtime of the logical path to the data object or collection
            identified by this option. Cannot be used with "seconds_since_epoch"
            parameter.

        Raises
        ------
        InvalidInputArgument
            If the path points to a collection.
        """
        if _logical_path._is_collection(self.sess, path):
            raise ex.InvalidInputArgument()

        _api_impl._touch_impl(self.sess, path, **options)
