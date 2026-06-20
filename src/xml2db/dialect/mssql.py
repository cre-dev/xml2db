import os
import shutil
import subprocess
import tempfile
from typing import Any, List, TYPE_CHECKING

from sqlalchemy import Index
from sqlalchemy.dialects import mssql as mssql_dialect

from .base import DatabaseDialect

if TYPE_CHECKING:
    from ..table.column import DataModelColumn


# Records below this count go through fast_executemany; at or above, BCP is used.
_BCP_THRESHOLD = 1000


class MSSQLDialect(DatabaseDialect):
    """Dialect for Microsoft SQL Server.

    MSSQL supports identifiers up to 128 characters, so no truncation is
    needed. Columnstore index support and MSSQL-specific type mappings are
    handled in this class.

    When the ``bcp`` utility is available on PATH and the connection uses SQL
    authentication, :meth:`bulk_insert` switches to BCP for batches of
    :data:`_BCP_THRESHOLD` rows or more. Smaller batches always use
    ``fast_executemany`` (enabled at engine level) to avoid BCP's subprocess
    overhead. Pass ``use_bcp=False`` to :class:`~xml2db.DataModel` to disable
    BCP entirely.
    """

    MAX_IDENTIFIER_LENGTH: int = 128

    def __init__(self, use_bcp: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.bcp_path = shutil.which("bcp") if use_bcp else None

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

    @staticmethod
    def _format_bcp_value(v: Any) -> str:
        """Format a Python value as a BCP character-mode field (tab-separated)."""
        if v is None:
            return ""
        if isinstance(v, bool):
            # Must precede int: bool is a subclass of int.
            return "1" if v else "0"
        if isinstance(v, (bytes, bytearray)):
            # BCP character mode accepts hex without 0x prefix for binary columns.
            return v.hex()
        s = str(v)
        # Tab is the field delimiter; replace any occurrence in string values.
        return s.replace("\t", " ")

    def bulk_insert(self, conn: Any, table: Any, records: list) -> None:
        """Bulk-insert records, using BCP for large batches when available.

        Batches smaller than :data:`_BCP_THRESHOLD` rows, or any batch when
        BCP is unavailable or the connection lacks SQL auth credentials, are
        handled by the base-class ``fast_executemany`` path.

        BCP does not participate in the caller's SQLAlchemy transaction.

        Args:
            conn: A SQLAlchemy ``Connection`` already within a transaction.
            table: The SQLAlchemy ``Table`` object to insert into.
            records: A list of dicts mapping column keys to Python values.
        """
        if not records:
            return

        url = conn.engine.url
        if (
            self.bcp_path is None
            or len(records) < _BCP_THRESHOLD
            or not url.username
            or not url.password
        ):
            super().bulk_insert(conn, table, records)
            return

        col_by_key = {col.key: col for col in table.columns}
        col_keys = [k for k in records[0] if k in col_by_key]

        # Python-side scalar defaults absent from records (same as other dialects).
        extra_defaults: dict = {}
        for col in table.columns:
            if col.key not in records[0] and col.key in col_by_key:
                d = col.default
                if d is not None and d.is_scalar:
                    extra_defaults[col.key] = d.arg

        all_col_keys = col_keys + list(extra_defaults.keys())

        full_name = (
            f"[{table.schema}].[{table.name}]"
            if table.schema
            else f"[{table.name}]"
        )

        fd, data_path = tempfile.mkstemp(suffix=".bcp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                for record in records:
                    row = []
                    for key in all_col_keys:
                        v = record.get(key) if key in col_keys else extra_defaults[key]
                        row.append(self._format_bcp_value(v))
                    f.write("\t".join(row) + "\n")

            cmd = [
                self.bcp_path, full_name, "in", data_path,
                "-S", f"{url.host},{url.port or 1433}",
                "-d", url.database,
                "-U", url.username,
                "-P", url.password,
                "-c",       # character (text) mode
                "-t", "\t", # tab field separator
                "-r", "\n", # newline row terminator
                "-k",       # empty field → NULL (not column default)
                "-b", "10000",
                "-C", "65001",  # UTF-8
            ]
            if str(url.query.get("TrustServerCertificate", "")).lower() == "yes":
                cmd.append("-u")  # trust server certificate (mssql-tools18)
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(
                    f"BCP failed (exit {result.returncode}):\n"
                    f"{result.stdout}\n{result.stderr}"
                )
        finally:
            if os.path.exists(data_path):
                os.unlink(data_path)
