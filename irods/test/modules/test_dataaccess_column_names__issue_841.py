"""Regression tests for issue #841 (wrong column names in the DataAccess model)."""
import unittest
from collections import OrderedDict

from irods.column import Criterion
from irods.message import empty_gen_query_out
from irods.models import Collection, DataAccess, DataObject, ModelBase
from irods.query import Query
from irods.results import ResultSet


class _SessionStateStub:
    """Provide sess.server_version == (4, 3, 4) for building a genquery offline (no server)."""

    server_version = (4, 3, 4)


# The strings iRODS itself defines as genquery1 column attributes; see
# lib/core/include/irods/rodsGenQueryNames.h in the iRODS server sources,
# where COL_DATA_ACCESS_NAME (the "#" define / C identifier) maps to the
# attribute string "DATA_ACCESS_NAME", COL_DATA_TOKEN_NAMESPACE to
# "DATA_TOKEN_NAMESPACE", etc.  Attribute strings carry no "COL_" prefix;
# the DataObject/Collection/RuleExec/...  models in irods/models.py follow
# this convention, and DataAccess.type (700) already did.
#
# Attempting a permission criterion from DataAccess as described in issue
# #841 (Criterion('=', DataAccess.name, 'own')) previously carried the
# mismatched "COL_"-prefixed names.
_IRODS_ATTRIBUTE_NAMES = OrderedDict(
    [
        (DataAccess.type, "DATA_ACCESS_TYPE"),
        (DataAccess.name, "DATA_ACCESS_NAME"),
        (DataAccess.token_namespace, "DATA_TOKEN_NAMESPACE"),
        (DataAccess.user_id, "DATA_ACCESS_USER_ID"),
        (DataAccess.data_id, "DATA_ACCESS_DATA_ID"),
    ]
)

_DATAACCESS_COLUMN_IDS = {700, 701, 702, 703, 704}


class TestDataAccessColumnNames(unittest.TestCase):
    """DataAccess model columns carry their iRODS genquery1 attribute names."""

    def test_dataaccess_request_columns_use_irods_attribute_names(self):
        """DataAccess columns built into a client-side genquery carry iRODS attribute names."""
        query = Query(_SessionStateStub(), DataObject.name, Collection.name, DataAccess)
        selected_ids = {c.icat_id for c in query.columns}
        self.assertGreaterEqual(selected_ids, _DATAACCESS_COLUMN_IDS)

        for column, expected_name in _IRODS_ATTRIBUTE_NAMES.items():
            self.assertEqual(
                column.icat_key, expected_name, f"{column!r} should be {expected_name!r} (got {column.icat_key!r})"
            )

    def test_criteria_built_from_dataaccess_columns_use_irods_attribute_names(self):
        """Criteria like Criterion("=", DataAccess.name, "own") are built on iRODS-named columns."""
        for attribute, expected in _IRODS_ATTRIBUTE_NAMES.items():
            criterion = Criterion("=", attribute, "own")
            self.assertEqual(criterion.query_key.icat_key, expected)

    def test_result_keys_surface_irods_attribute_names(self):
        """Result rows keyed via ModelBase.columns()[attriInx] surface the iRODS attribute names (results.py)."""
        query = Query(_SessionStateStub(), DataAccess)
        raw = empty_gen_query_out(list(query.columns.keys()))
        result = ResultSet(raw)
        keys = {c.attriInx: ModelBase.columns()[c.attriInx] for c in result.cols}
        self.assertEqual(set(keys), _DATAACCESS_COLUMN_IDS)
        for column, expected_name in _IRODS_ATTRIBUTE_NAMES.items():
            self.assertEqual(keys[column.icat_id].icat_key, expected_name)
            self.assertEqual(keys[column.icat_id], column)

    def test_no_dataaccess_column_name_carries_the_col_prefix(self):
        """No DataAccess column name keeps the COL_ prefix (700 already had none; #841)."""
        columns_by_id = {
            DataAccess.type.icat_id: DataAccess.type,
            DataAccess.name.icat_id: DataAccess.name,
            DataAccess.token_namespace.icat_id: DataAccess.token_namespace,
            DataAccess.user_id.icat_id: DataAccess.user_id,
            DataAccess.data_id.icat_id: DataAccess.data_id,
        }
        self.assertEqual(set(columns_by_id), _DATAACCESS_COLUMN_IDS)
        for column in columns_by_id.values():
            self.assertFalse(column.icat_key.startswith("COL_"), f"unexpected 'COL_' prefix in {column!r}")
