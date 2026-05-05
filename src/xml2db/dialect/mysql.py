from typing import Any, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.dialects import mysql as mysql_dialect

from .base import DatabaseDialect

if TYPE_CHECKING:
    from ..table.column import DataModelColumn


class MySQLDialect(DatabaseDialect):
    """Dialect for MySQL / MariaDB.

    MySQL enforces a 64-character limit on identifiers.
    """

    MAX_IDENTIFIER_LENGTH: int = 64

    def column_type(self, col: "DataModelColumn", temp: bool) -> Any:
        if col.occurs[1] != 1:
            return String(4000)
        if col.data_type in ["string", "NMTOKEN", "duration", "token"]:
            if col.max_length is None:
                return String(255)
        if col.data_type == "binary":
            if col.max_length == col.min_length:
                return mysql_dialect.BINARY(col.max_length)
            return mysql_dialect.VARBINARY(col.max_length)
        return super().column_type(col, temp)
