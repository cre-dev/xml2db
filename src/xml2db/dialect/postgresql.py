import csv
import io
from typing import Any

from .base import DatabaseDialect

# PostgreSQL COPY is in-protocol (no temp file), so the default threshold is 0
# (COPY is always used for supported drivers regardless of batch size).
_COPY_THRESHOLD = 0


class PostgreSQLDialect(DatabaseDialect):
    """Dialect for PostgreSQL.

    PostgreSQL enforces a 63-character limit on identifiers. Names exceeding
    this limit are truncated with a hash suffix by the base
    :meth:`~DatabaseDialect.db_identifier` implementation, which uses
    :attr:`MAX_IDENTIFIER_LENGTH` to decide when to truncate.
    """

    MAX_IDENTIFIER_LENGTH: int = 63

    def bulk_insert(
        self,
        conn: Any,
        table: Any,
        records: list,
        *,
        bulk_load: bool | None = None,
        bulk_load_threshold: int | None = None,
    ) -> None:
        """Bulk-insert records via PostgreSQL's ``COPY FROM STDIN``.

        Builds an in-memory CSV payload and streams it to the server using
        the driver's native COPY protocol.  Supported drivers:

        - **psycopg2** — uses ``cursor.copy_expert()``.
        - **psycopg** (psycopg3) — uses ``cursor.copy()``.

        Falls back to the base-class parameterised executemany for any other
        driver (or when ``bulk_load=False``).

        Args:
            conn: A SQLAlchemy ``Connection`` already within a transaction.
            table: The SQLAlchemy ``Table`` object to insert into.
            records: A list of dicts mapping column keys to Python values.
            bulk_load: ``True`` — require COPY (raise if driver unsupported);
                ``False`` — always use executemany; ``None`` (default) — use
                COPY when available, fall back silently.
            bulk_load_threshold: Minimum number of records to trigger COPY.
                Defaults to :data:`_COPY_THRESHOLD` (0 — always use COPY for
                supported drivers).
        """
        if not records:
            return

        threshold = bulk_load_threshold if bulk_load_threshold is not None else _COPY_THRESHOLD
        driver = conn.dialect.driver

        if driver not in ("psycopg2", "psycopg"):
            if bulk_load is True:
                raise RuntimeError(
                    f"bulk_load=True requires the psycopg2 or psycopg driver, got '{driver}'. "
                    f"Use a postgresql+psycopg2:// or postgresql+psycopg:// connection string."
                )
            super().bulk_insert(conn, table, records)
            return

        if bulk_load is False or len(records) < threshold:
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
