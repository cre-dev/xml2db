import csv
import io
from typing import Any

from .base import DatabaseDialect


class PostgreSQLDialect(DatabaseDialect):
    """Dialect for PostgreSQL.

    PostgreSQL enforces a 63-character limit on identifiers. Names exceeding
    this limit are truncated with a hash suffix by the base
    :meth:`~DatabaseDialect.db_identifier` implementation, which uses
    :attr:`MAX_IDENTIFIER_LENGTH` to decide when to truncate.
    """

    MAX_IDENTIFIER_LENGTH: int = 63

    def bulk_insert(self, conn: Any, table: Any, records: list) -> None:
        """Bulk-insert records via PostgreSQL's ``COPY FROM STDIN``.

        Builds an in-memory CSV payload and streams it to the server using
        the driver's native COPY protocol.  Supported drivers:

        - **psycopg2** — uses ``cursor.copy_expert()``.
        - **psycopg** (psycopg3) — uses ``cursor.copy()``.

        Falls back to the base-class parameterised executemany for any other
        driver.

        Args:
            conn: A SQLAlchemy ``Connection`` already within a transaction.
            table: The SQLAlchemy ``Table`` object to insert into.
            records: A list of dicts mapping column keys to Python values.
        """
        if not records:
            return

        driver = conn.dialect.driver
        if driver not in ("psycopg2", "psycopg"):
            super().bulk_insert(conn, table, records)
            return

        col_by_key = {col.key: col for col in table.columns}
        col_keys = [k for k in records[0] if k in col_by_key]

        # Python-side scalar defaults absent from records (e.g. default=False).
        # executemany applies these automatically; our COPY path must do it manually.
        extra_defaults: dict = {}
        for col in table.columns:
            if col.key not in records[0] and col.key in col_by_key:
                d = col.default
                if d is not None and d.is_scalar:
                    extra_defaults[col.key] = d.arg

        all_col_keys = col_keys + list(extra_defaults.keys())

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(all_col_keys)
        for record in records:
            row = []
            for key in all_col_keys:
                v = record.get(key) if key in col_keys else extra_defaults[key]
                if v is None:
                    row.append("")
                elif isinstance(v, bytes):
                    # PostgreSQL bytea hex format: \xDEADBEEF
                    row.append("\\x" + v.hex())
                elif isinstance(v, bool):
                    # bool must precede the general str() path: bool subclasses int,
                    # so str(True) → '1' which PostgreSQL COPY rejects for boolean.
                    row.append("true" if v else "false")
                else:
                    # str() on datetime → "YYYY-MM-DD HH:MM:SS[.f][±HH:MM]",
                    # which PostgreSQL's text input parser accepts.
                    row.append(str(v))
            writer.writerow(row)
        buf.seek(0)

        col_names = ", ".join(f'"{col_by_key[k].name}"' for k in all_col_keys)
        full_name = (
            f'"{table.schema}"."{table.name}"'
            if table.schema
            else f'"{table.name}"'
        )
        copy_sql = (
            f"COPY {full_name} ({col_names}) FROM STDIN "
            f"WITH (FORMAT CSV, HEADER, NULL '')"
        )

        raw_conn = conn.connection.dbapi_connection
        if driver == "psycopg2":
            cur = raw_conn.cursor()
            cur.copy_expert(copy_sql, buf)
        else:  # psycopg3
            cur = raw_conn.cursor()
            with cur.copy(copy_sql) as copy:
                copy.write(buf.read().encode("utf-8"))
