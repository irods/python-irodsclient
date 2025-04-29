import contextlib
import os
import sys
from irods import env_filename_from_keyword_args
import irods.exception as ex
from irods.message import ET, XML_Parser_Type, IRODS_VERSION
from irods.path import iRODSPath
from irods.session import iRODSSession

__all__ = [
    "make_session",
    "home_collection",
    "xml_mode",
    "get_collection",
    "get_data_object",
]

class StopTestsException(Exception):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "unittest" in sys.modules.keys():
            print("Aborting tests [ Got : %r ]" % self, file=sys.stderr)
            os.abort()


class iRODS_Server_Too_Recent_For_Testing(StopTestsException):
    pass


def _get_server_version_for_test(session, curtail_length):
    return session._server_version(session.GET_SERVER_VERSION_WITHOUT_AUTH)[
        :curtail_length
    ]


# Create a connection for test, based on ~/.irods environment by default.


def make_session(test_server_version=False, **kwargs):
    """Connect to an iRODS server as determined by any client environment
    file present at a standard location, and by any keyword arguments given.

    Arguments:

    test_server_version: Of type bool; in the `irods.test.helpers` version of this
                         function, defaults to True.  A True value causes
                         *iRODS_Server_Too_Recent* to be raised if the server
                         connected to is more recent than the current Python iRODS
                         client's advertised level of compatibility.

    **kwargs:            Keyword arguments.  Fed directly to the iRODSSession
                         constructor."""

    env_file = env_filename_from_keyword_args(kwargs)
    session = iRODSSession(irods_env_file=env_file, **kwargs)
    if test_server_version:
        connected_version = _get_server_version_for_test(session, curtail_length=3)
        advertised_version = IRODS_VERSION[:3]
        if connected_version > advertised_version:
            msg = (
                "Connected server is {connected_version}, "
                "but this python-irodsclient advertises compatibility up to {advertised_version}."
            ).format(**locals())
            raise iRODS_Server_Too_Recent_For_Testing(msg)

    return session


def home_collection(session):
    """Return a string value for the given session's home collection."""
    return "/{0.zone}/home/{0.username}".format(session)


@contextlib.contextmanager
def xml_mode(s):
    """In a with-block, this context manager can temporarily change the client's choice of XML parser.

    Example usages:
        with("QUASI_XML"):
            # ...
        with(XML_Parser_Type.QUASI_XML):
            # ..."""

    try:
        if isinstance(s, str):
            ET(getattr(XML_Parser_Type, s))  # e.g. xml_mode("QUASI_XML")
        elif isinstance(s, XML_Parser_Type):
            ET(s)  # e.g. xml_mode(XML_Parser_Type.QUASI_XML)
        else:
            msg = "xml_mode argument must be a string (e.g. 'QUASI_XML') or an XML_Parser_Type enum."
            raise ValueError(msg)
        yield
    finally:
        ET(None)


class _unlikely_value:
    pass


@contextlib.contextmanager
def temporarily_assign_attribute(
    target, attr, value, not_set_indicator=_unlikely_value()
):
    save = not_set_indicator
    try:
        save = getattr(target, attr, not_set_indicator)
        setattr(target, attr, value)
        yield
    finally:
        if save != not_set_indicator:
            setattr(target, attr, save)
        else:
            delattr(target, attr)


def get_data_object(sess, logical_path):
    """Get a reference to the data object (as an iRODSDataObject) at the given path, if one is found.
    Else, return None.

    Parameters:
        sess: an authenticated session object.
        logical_path: the full logical path where the data object is to be found.  Can be in unnormalized form.
    """
    try:
        # Check for a data object at the normalized path.
        return sess.data_objects.get(iRODSPath(logical_path))
    except ex.DataObjectDoesNotExist:
        return None


def get_collection(sess, logical_path):
    """Get a reference to the collection (as an iRODSCollection) at the given path, if one is found.
    Else, return None.

    Parameters:
        sess: an authenticated session object.
        logical_path: the full logical path where the collection is to be found.  Can be in unnormalized form.
    """
    try:
        # Path normalization is internal to this call.
        return sess.collections.get(logical_path)
    except ex.CollectionDoesNotExist:
        return None


# Utility class and factory function for storing the original value of variables within the given namespace.
def create_value_cache(namespace:dict):
    class CachedValues:
        __namespace = namespace

        @classmethod
        def make_entry(cls, name):
            cached_value = cls.__namespace[name]
            setattr(cls,name,property(lambda self: cached_value))

    return CachedValues()
