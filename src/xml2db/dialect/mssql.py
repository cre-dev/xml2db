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
_BCP_THRESHOLD = 100


class MSSQLDialect(DatabaseDialect):
    """Dialect for Microsoft SQL Server.

    MSSQL supports identifiers up to 128 characters, so no truncation is
    needed. Columnstore index support and MSSQL-specific type mappings are
    handled in this class.

    When the ``bcp`` utility is available on PATH and the connection uses SQL
    authentication or a trusted connection, :meth:`bulk_insert` switches to BCP
    for batches of :data:`_BCP_THRESHOLD` rows or more. Smaller batches always
    use ``fast_executemany`` (enabled at engine level) to avoid BCP's subprocess
    overhead.
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

    def create_engine(self, connection_string: str, **kwargs: Any) -> Any:
        """Create a MSSQL engine with ``fast_executemany`` and ``SERIALIZABLE`` isolation."""
        kwargs.setdefault("fast_executemany", True)
        kwargs.setdefault("isolation_level", "SERIALIZABLE")
        return super().create_engine(connection_string, **kwargs)

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

    def bulk_insert(
        self,
        conn: Any,
        table: Any,
        records: list,
        *,
        bulk_load: bool | None = None,
        bulk_load_threshold: int | None = None,
    ) -> None:
        """Bulk-insert records, using BCP for large batches when available.

        Batches smaller than the effective threshold, or any batch when
        ``bulk_load=False``, use ``fast_executemany`` unconditionally.

        When ``bulk_load=True`` and the batch meets the threshold but BCP
        prerequisites are not satisfied (binary not on PATH, unsupported auth),
        a :class:`RuntimeError` is raised with an actionable message.

        SQL auth uses ``-U``/``-P``; Kerberos/Windows auth uses ``-T``.
        BCP does not participate in the caller's SQLAlchemy transaction.

        Args:
            conn: A SQLAlchemy ``Connection`` already within a transaction.
            table: The SQLAlchemy ``Table`` object to insert into.
            records: A list of dicts mapping column keys to Python values.
            bulk_load: ``True`` to require BCP (raise if unavailable for this
                batch), ``False`` to always use fast_executemany, or ``None``
                (default) to use BCP when available and fall back silently.
            bulk_load_threshold: Override the minimum batch size for BCP.
                Defaults to :data:`_BCP_THRESHOLD` (100).
        """
        if not records:
            return

        threshold = bulk_load_threshold if bulk_load_threshold is not None else _BCP_THRESHOLD

        # bulk_load=False or batch too small → always use fast_executemany.
        if bulk_load is False or len(records) < threshold:
            super().bulk_insert(conn, table, records)
            return

        # Check BCP prerequisites.
        url = conn.engine.url
        trusted = str(url.query.get("Trusted_Connection", "")).lower() == "yes"
        has_sql_auth = bool(url.username and url.password)
        bcp_path = shutil.which("bcp")

        if bcp_path is None:
            if bulk_load is True:
                raise RuntimeError(
                    "bulk_load=True requires the bcp utility on PATH. "
                    "Install mssql-tools (Linux/macOS) or SQL Server Command Line Utilities "
                    "(Windows), or set bulk_load=False to use fast_executemany instead."
                )
            super().bulk_insert(conn, table, records)
            return

        if not has_sql_auth and not trusted:
            if bulk_load is True:
                raise RuntimeError(
                    "bulk_load=True requires SQL Server authentication (username and password "
                    "in the connection string) or a Windows/Kerberos trusted connection "
                    "(Trusted_Connection=yes in the connection string query parameters). "
                    "Set bulk_load=False to use fast_executemany instead."
                )
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
                bcp_path, full_name, "in", data_path,
                "-S", f"{url.host},{url.port or 1433}",
                "-d", url.database,
                "-c",       # character (text) mode
                "-t", "\t", # tab field separator
                "-r", "\n", # newline row terminator
                "-k",       # empty field → NULL (not column default)
                "-b", "10000",
                "-C", "65001",  # UTF-8
            ]
            if has_sql_auth:
                cmd += ["-U", url.username, "-P", url.password]
            else:
                cmd.append("-T")  # Kerberos / Windows trusted connection
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
