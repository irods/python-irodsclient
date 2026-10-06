
from enum import Enum
from ..api_number import api_number
from .low_level.message import MetadataRequest, iRODSMessage

class irods_object_type(Enum):
    DATA_OBJECT = '-d'
    RESOURCE = '-R'
    USER = '-u'
    COLLECTION = '-C'

# op can be : "set", "add", "rm"

def avu_operation(
    conn,
    object_type: irods_object_type,
    op, /,
    path,
    avu,
    **opt):
    """
    Applies an AVU operation with a direct calling to the iRODS Metadata API.

    Args:
        conn: The Connection object.
        object_type:
            One of DATA_OBJECT, RESOURCE, USER, or COLLECTION, whichever describes the target object for the 'avu'.
        op: One of "add", "set", or "rm"
        path: The name or logical path of the target object for the 'avu'.
        avu: A sequence containing (name, value[, units]). All sequence members must be strings.
        **opt: options to be applied in the metadata API call.
    
    Returns:
        None

    Raises:
        An iRODSException corresponding to the particular server error, in case of the API returning a nonzero status code.
    """

    message_body = MetadataRequest(
        op, object_type.value, path, *avu, **opt
    )

    request = iRODSMessage(
        "RODS_API_REQ",
        msg=message_body, int_info=api_number["MOD_AVU_METADATA_AN"]
    )
    conn.send(request)
    response = conn.recv()
