import csv
import os
import tempfile
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Double,
    Integer,
    LargeBinary,
    Sequence,
    SmallInteger,
    text,
)
from sqlalchemy.exc import ProgrammingError
import sqlalchemy.schema

from .base import DatabaseDialect


class DuckDBDialect(DatabaseDialect):
    """Dialect for DuckDB.

    DuckDB supports very long identifiers (effectively unlimited in practice;
    we document 1024 as a safe upper bound). It requires two workarounds:

    - **Primary key columns**: DuckDB does not support ``autoincrement`` in the
      same way as other backends. A ``Sequence`` object is used instead.
    - **Schema creation**: DuckDB's inspector does not reliably list schemas
      before they exist, so the existence check is replaced with a try/except
      around ``CREATE SCHEMA``.
    """

    # this limit comes from the implementation with SQLAlchemy and not a constraint of duckdb per se
    MAX_IDENTIFIER_LENGTH: int = 63

    def pk_column(self, table_name: str) -> Column:
        """Return a Sequence-based primary key column for DuckDB."""
        logical = f"pk_{table_name}"
        pk_sequence = Sequence(self.db_identifier(f"pk_sequ_{table_name}"))
        return Column(
            self.db_identifier(logical),
            Integer,
            pk_sequence,
            server_default=pk_sequence.next_value(),
            primary_key=True,
            key=logical,
        )

    def create_schema(self, engine: Any, schema_name: str) -> None:
        """Create a schema using try/except, as required by DuckDB."""

        def do_create() -> None:
            with engine.connect() as conn:
                conn.execute(sqlalchemy.schema.CreateSchema(schema_name))
                conn.commit()

        try:
            do_create()
        except ProgrammingError:
            pass

    # Maps SQLAlchemy column types to DuckDB CAST target type names.
    # String types need no cast; LargeBinary is handled via unhex().
    # Order matters: subclasses (BigInteger, SmallInteger) must appear before
    # their parent (Integer) so that isinstance() matches the most specific type.
    _DUCKDB_CAST: dict = {
        BigInteger: "BIGINT",
        SmallInteger: "SMALLINT",
        Integer: "INTEGER",
        Double: "DOUBLE",
        Boolean: "BOOLEAN",
        DateTime: "TIMESTAMPTZ",  # DateTime(timezone=False) → TIMESTAMP below
    }

    def _select_expr(self, key: str, col: Any) -> str:
        """Return a DuckDB SELECT expression that casts a VARCHAR CSV column."""
        if isinstance(col.type, LargeBinary):
            return f'unhex("{key}")'
        for sa_type, duckdb_type in self._DUCKDB_CAST.items():
            if isinstance(col.type, sa_type):
                if isinstance(col.type, DateTime) and not col.type.timezone:
                    duckdb_type = "TIMESTAMP"
                return f'CAST("{key}" AS {duckdb_type})'
        return f'"{key}"'  # String / unknown: keep as VARCHAR

    def bulk_insert(self, conn: Any, table: Any, records: list) -> None:
        """Bulk-insert records via a temporary CSV file and DuckDB's ``read_csv``.

        All CSV columns are read as VARCHAR (``all_varchar=true``) and then
        explicitly cast to their target types in the ``SELECT`` clause.
        Binary columns are hex-encoded in the CSV and decoded with ``unhex()``.

        Args:
            conn: A SQLAlchemy ``Connection`` already within a transaction.
            table: The SQLAlchemy ``Table`` object to insert into.
            records: A list of dicts mapping column keys to Python values.
        """
        if not records:
            return

        # Map column key -> SQLAlchemy Column object
        col_by_key = {col.key: col for col in table.columns}

        # Columns present in the first record that correspond to table columns
        col_keys = [k for k in records[0] if k in col_by_key]

        # SQLAlchemy Python-side scalar defaults (e.g. default=False on temp_exists)
        # are applied automatically by executemany but not by our CSV path.
        extra_defaults: dict = {}
        for col in table.columns:
            if col.key not in records[0] and col.key in col_by_key:
                d = col.default
                if d is not None and d.is_scalar:
                    extra_defaults[col.key] = d.arg

        all_col_keys = col_keys + list(extra_defaults.keys())

        fd, csv_path = tempfile.mkstemp(suffix=".csv")
        try:
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(all_col_keys)
                for record in records:
                    row = []
                    for key in all_col_keys:
                        v = record.get(key) if key in col_keys else extra_defaults[key]
                        if v is None:
                            row.append("")
                        elif isinstance(v, bytes):
                            row.append(v.hex())
                        elif isinstance(v, bool):
                            # Must come before the general str() path since bool is a
                            # subclass of int, and csv.writer would write 0/1 otherwise.
                            row.append("true" if v else "false")
                        else:
                            # str() on datetime gives "YYYY-MM-DD HH:MM:SS[.f][+HH:MM]",
                            # which DuckDB's CAST accepts without ambiguity.
                            row.append(str(v))
                    writer.writerow(row)

            full_name = (
                f'"{table.schema}"."{table.name}"'
                if table.schema
                else f'"{table.name}"'
            )
            insert_cols = ", ".join(
                f'"{col_by_key[k].name}"' for k in all_col_keys
            )
            select_exprs = ", ".join(
                self._select_expr(k, col_by_key[k]) for k in all_col_keys
            )
            # DuckDB requires forward slashes in file paths on all platforms.
            safe_path = csv_path.replace("\\", "/")
            sql = text(
                f"INSERT INTO {full_name} ({insert_cols}) "
                f"SELECT {select_exprs} "
                f"FROM read_csv('{safe_path}', header=true, nullstr='', all_varchar=true, quote='\"', escape='\"')"
            )
            conn.execute(sql)
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)
