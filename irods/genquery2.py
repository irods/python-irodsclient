import json

from irods.api_number import api_number
from irods.exception import OperationNotSupported
from irods.message import GenQuery2Request, STR_PI, iRODSMessage


class GenQuery2:
    """Interface to the GenQuery2 API

    This class provides an interface to the GenQuery2 API, an experimental
    iRODS API for querying iRODS. GenQuery2 is an improved version of the
    traditional GenQuery interface. The GenQuery2 interface may be subject
    to change.
    """

    def __init__(self, session):
        self.session = session
        if not self._is_supported():
            raise OperationNotSupported(
                "GenQuery2 is not supported by default on this iRODS version."
            )

    def execute(self, query, zone=None):
        """Execute this GenQuery2 query, and return the results."""
        effective_zone = self.session.zone if zone is None else zone
        return json.loads(self._exec_genquery2(query, effective_zone))

    def get_sql(self, query, zone=None):
        """Return the SQL query that this GenQuery2 query will be translated to."""
        effective_zone = self.session.zone if zone is None else zone
        return self._exec_genquery2(query, effective_zone, sql_flag=True)

    def get_column_mappings(self, zone=None):
        effective_zone = self.session.zone if zone is None else zone
        return json.loads(
            self._exec_genquery2("", effective_zone, column_mappings_flag=True)
        )

    def _exec_genquery2(self, query, zone, sql_flag=False, column_mappings_flag=False):
        msg = GenQuery2Request()
        msg.query_string = query
        msg.zone = zone
        msg.sql_only = 1 if sql_flag else 0
        msg.column_mappings = 1 if column_mappings_flag else 0
        message = iRODSMessage(
            "RODS_API_REQ", msg=msg, int_info=api_number["GENQUERY2_AN"]
        )
        with self.session.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
        return response.get_main_message(STR_PI).myStr

    def _is_supported(self):
        """Checks whether this iRODS server supports GenQuery2."""
        return self.session.server_version >= (4, 3, 2)
