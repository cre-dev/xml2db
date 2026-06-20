import os
import tempfile
from typing import Any, TYPE_CHECKING

from sqlalchemy import LargeBinary, String, text
from sqlalchemy.dialects import mysql as mysql_dialect
from sqlalchemy.exc import OperationalError

from .base import DatabaseDialect

if TYPE_CHECKING:
    from ..table.column import DataModelColumn

# MySQL error codes for "LOAD DATA LOCAL INFILE not available".
_LOCAL_INFILE_ERRORS = (1148, 3948)

# Records below this count skip LOAD DATA LOCAL INFILE (temp-file overhead).
_LOAD_DATA_THRESHOLD = 100


class MySQLDialect(DatabaseDialect):
    """Dialect for MySQL / MariaDB.

    MySQL enforces a 64-character limit on identifiers.

    :meth:`bulk_insert` uses ``LOAD DATA LOCAL INFILE`` for the ``pymysql``
    and ``mysqldb`` drivers when the batch meets :data:`_LOAD_DATA_THRESHOLD`.
    The engine must be created via :class:`~xml2db.model.DataModel` (which
    injects ``local_infile=True`` automatically) or with
    ``connect_args={"local_infile": True}``, and the MySQL server must have
    ``local_infile=ON``.
    """

    # further reducing the max length because SQL Alchemy adds suffixes to foreign key names
    MAX_IDENTIFIER_LENGTH: int = 56

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        # Tri-state cache: None = not yet tested, True = works, False = unavailable.
        self._local_infile_ok: bool | None = None

    def create_engine(self, connection_string: str, **kwargs: Any) -> Any:
        """Create a MySQL engine with ``local_infile=True`` in connect_args."""
        connect_args = kwargs.pop("connect_args", {})
        connect_args.setdefault("local_infile", True)
        return super().create_engine(connection_string, connect_args=connect_args, **kwargs)

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

    @staticmethod
    def _format_value(v: Any, col: Any) -> str:
        """Format a Python value for MySQL LOAD DATA LOCAL INFILE (tab-separated).

        NULL → ``\\N``.  Binary columns are hex-encoded (decoded server-side
        with UNHEX()).  Booleans become ``1``/``0``.  Strings have backslashes
        and the field/line delimiters escaped so MySQL's default ESCAPED BY
        handler reconstructs the original text.
        """
        if v is None:
            return "\\N"
        if isinstance(col.type, LargeBinary):
            # Decoded server-side via UNHEX(); transmit as plain hex string.
            return bytes(v).hex() if isinstance(v, (bytes, bytearray, memoryview)) else ""
        if isinstance(v, bool):
            # Must precede int: bool subclasses int.
            return "1" if v else "0"
        s = str(v)
        # Escape backslash first, then the characters MySQL's LOAD DATA
        # interprets as special under ESCAPED BY '\\'.
        s = s.replace("\\", "\\\\")
        s = s.replace("\n", "\\n")
        s = s.replace("\r", "\\r")
        s = s.replace("\t", "\\t")
        return s

    def bulk_insert(
        self,
        conn: Any,
        table: Any,
        records: list,
        *,
        bulk_load: bool | None = None,
        bulk_load_threshold: int | None = None,
    ) -> None:
        """Bulk-insert records via MySQL's ``LOAD DATA LOCAL INFILE``.

        Builds a tab-separated temp file and streams it to the server using
        the driver's ``LOAD DATA LOCAL INFILE`` protocol.  Supported drivers:

        - **pymysql**: the engine must have ``local_infile=True`` in
          ``connect_args`` (set automatically by :meth:`create_engine`).
        - **mysqldb** (mysqlclient): same requirement.

        Falls back to the base-class parameterised executemany for other
        drivers or when ``LOAD DATA LOCAL INFILE`` is unavailable.

        Binary columns are hex-encoded in the file and decoded server-side
        with ``UNHEX()``.

        Args:
            conn: A SQLAlchemy ``Connection`` already within a transaction.
            table: The SQLAlchemy ``Table`` object to insert into.
            records: A list of dicts mapping column keys to Python values.
            bulk_load: ``True`` to require LOAD DATA LOCAL INFILE (raise if
                unavailable), ``False`` to always use executemany, or ``None``
                (default) to use LOAD DATA when available and fall back silently.
            bulk_load_threshold: Override the minimum batch size to trigger
                LOAD DATA LOCAL INFILE.  Defaults to
                :data:`_LOAD_DATA_THRESHOLD` (100).
        """
        if not records:
            return

        threshold = bulk_load_threshold if bulk_load_threshold is not None else _LOAD_DATA_THRESHOLD
        driver = conn.dialect.driver

        # Unsupported driver.
        if driver not in ("pymysql", "mysqldb"):
            if bulk_load is True:
                raise RuntimeError(
                    f"bulk_load=True requires the pymysql or mysqldb driver, got '{driver}'. "
                    f"Use a mysql+pymysql:// or mysql+mysqldb:// connection string."
                )
            super().bulk_insert(conn, table, records)
            return

        # bulk_load=False or batch too small → use executemany.
        if bulk_load is False or len(records) < threshold:
            super().bulk_insert(conn, table, records)
            return

        # Cached failure: LOAD DATA LOCAL INFILE is known to be unavailable.
        if self._local_infile_ok is False:
            if bulk_load is True:
                raise RuntimeError(
                    "bulk_load=True requires LOAD DATA LOCAL INFILE, but it is unavailable on "
                    "this connection. Enable local_infile on the MySQL server and ensure the "
                    "engine is created via DataModel (which sets local_infile=True automatically) "
                    "or with connect_args={'local_infile': True}."
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

        fd, tsv_path = tempfile.mkstemp(suffix=".tsv")
        _fallback = False
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                for record in records:
                    row = []
                    for k in all_col_keys:
                        v = record.get(k) if k in col_keys else extra_defaults[k]
                        row.append(self._format_value(v, col_by_key[k]))
                    f.write("\t".join(row) + "\n")

            full_name = (
                f"`{table.schema}`.`{table.name}`"
                if table.schema
                else f"`{table.name}`"
            )

            # Binary columns use a user variable so UNHEX() can be applied in
            # the SET clause; all other columns are addressed by name directly.
            col_list_parts = []
            set_parts = []
            for k in all_col_keys:
                col = col_by_key[k]
                if isinstance(col.type, LargeBinary):
                    var = f"@__hex_{col.name}"
                    col_list_parts.append(var)
                    set_parts.append(f"`{col.name}` = UNHEX({var})")
                else:
                    col_list_parts.append(f"`{col.name}`")

            col_clause = "(" + ", ".join(col_list_parts) + ")"
            set_clause = (" SET " + ", ".join(set_parts)) if set_parts else ""

            sql = (
                f"LOAD DATA LOCAL INFILE '{tsv_path}' "
                f"INTO TABLE {full_name} "
                f"CHARACTER SET utf8mb4 "
                f"FIELDS TERMINATED BY '\\t' ESCAPED BY '\\\\' "
                f"LINES TERMINATED BY '\\n' "
                f"{col_clause}{set_clause}"
            )

            try:
                conn.execute(text(sql))
                self._local_infile_ok = True
            except OperationalError as exc:
                orig = getattr(exc, "orig", None)
                code = orig.args[0] if orig and orig.args else None
                if code in _LOCAL_INFILE_ERRORS:
                    self._local_infile_ok = False
                    if bulk_load is True:
                        raise RuntimeError(
                            "bulk_load=True requires LOAD DATA LOCAL INFILE, but it is "
                            "unavailable on this connection (MySQL error "
                            f"{code}). Enable local_infile on the MySQL server and ensure "
                            "the engine is created via DataModel (which sets local_infile=True "
                            "automatically) or with connect_args={'local_infile': True}."
                        ) from exc
                    _fallback = True
                else:
                    raise
        finally:
            if os.path.exists(tsv_path):
                os.unlink(tsv_path)

        if _fallback:
            super().bulk_insert(conn, table, records)
