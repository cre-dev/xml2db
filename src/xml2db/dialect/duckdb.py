from typing import Any

from sqlalchemy import Column, Integer, Sequence
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

    MAX_IDENTIFIER_LENGTH: int = 1024

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
