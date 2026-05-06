from typing import Any, List, TYPE_CHECKING

from sqlalchemy import Index
from sqlalchemy.dialects import mssql as mssql_dialect

from .base import DatabaseDialect

if TYPE_CHECKING:
    from ..table.column import DataModelColumn


class MSSQLDialect(DatabaseDialect):
    """Dialect for Microsoft SQL Server.

    MSSQL supports identifiers up to 128 characters, so no truncation is
    needed. Columnstore index support and MSSQL-specific type mappings are
    handled in this class.
    """

    MAX_IDENTIFIER_LENGTH: int = 128

    def validate_table_config(self, config: dict) -> dict:
        """Allow ``as_columnstore`` through unchanged for MSSQL."""
        return config

    def validate_model_config(self, config: dict) -> dict:
        """Allow ``as_columnstore`` through unchanged for MSSQL."""
        return config

    def column_type(self, col: "DataModelColumn", temp: bool) -> Any:
        if col.occurs[1] != 1:
            return mssql_dialect.VARCHAR(8000)
        if col.data_type == "dateTime":
            # using DATETIMEOFFSET directly in the temporary table caused issues when inserting data
            # INSERT INTO SELECT converts datetime VARCHAR to DATETIMEOFFSET without errors
            return mssql_dialect.VARCHAR(100) if temp else mssql_dialect.DATETIMEOFFSET
        if col.data_type == "date":
            return mssql_dialect.VARCHAR(16)
        if col.data_type == "time":
            return mssql_dialect.VARCHAR(18)
        if col.data_type in ["string", "NMTOKEN", "duration", "token"]:
            if col.max_length is None:
                return mssql_dialect.VARCHAR(1000)
            min_length = 0 if col.min_length is None else col.min_length
            if min_length >= col.max_length - 1 and not col.allow_empty:
                return mssql_dialect.CHAR(col.max_length)
            return mssql_dialect.VARCHAR(col.max_length)
        if col.data_type == "binary":
            if col.max_length == col.min_length:
                return mssql_dialect.BINARY(col.max_length)
            return mssql_dialect.VARBINARY(col.max_length)
        return super().column_type(col, temp)

    def extra_indexes(self, table_name: str, config: dict) -> List[Index]:
        if config.get("as_columnstore"):
            return [
                Index(
                    self.db_identifier(f"idx_{table_name}_columnstore"),
                    mssql_clustered=True,
                    mssql_columnstore=True,
                )
            ]
        return []

    def relation_extra_indexes(
        self, rel_table_name: str, fk_self_col: str, fk_other_col: str, config: dict
    ) -> tuple:
        return (
            Index(
                self.db_identifier(f"ix_fk_{rel_table_name}"),
                self.db_identifier(fk_self_col),
                self.db_identifier(fk_other_col),
                mssql_clustered=True,
            ),
        )
