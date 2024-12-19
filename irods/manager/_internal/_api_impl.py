from irods.api_number import api_number
from irods.message import iRODSMessage, JSON_Message


def _touch_impl(session, path, **options):
    with session.pool.get_connection() as conn:
        message_body = JSON_Message(
            {"logical_path": path, "options": options}, conn.server_version
        )
        message = iRODSMessage(
            "RODS_API_REQ", msg=message_body, int_info=api_number["TOUCH_APN"]
        )
        conn.send(message)
        response = conn.recv()
