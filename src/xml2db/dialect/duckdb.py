from typing import Any

from sqlalchemy import Column, Integer, Sequence
from sqlalchemy.exc import ProgrammingError
import sqlalchemy.schema

from .base import DatabaseDialect


class DuckDBDialect(DatabaseDialect):
    """Dialect for DuckDB.

    DuckDB supports very long identifiers (effectively unlimited in practice;
    we document 1024 as a safe upper bound). It does require two workarounds
    that will be migrated into this class in step 4 of the migration plan:

    - **Primary key columns**: DuckDB does not support ``autoincrement`` in the
      same way as other backends. A ``Sequence`` object must be used instead.
      The :meth:`pk_column` override will encapsulate this.
    - **Schema creation**: DuckDB's inspector does not reliably list schemas
      before they exist, so the existence check must be replaced with a
      try/except around ``CREATE SCHEMA``. The :meth:`create_schema` override
      will encapsulate this.

    Both overrides are stubbed here as pass-throughs so the class exists and
    is registered. The real implementations will replace these stubs in step 4.
    """

    MAX_IDENTIFIER_LENGTH: int = 1024

    def pk_column(self, table_name: str) -> Column:
        """Return a Sequence-based primary key column for DuckDB.

        .. note::
            This stub delegates to the base implementation. The DuckDB-specific
            ``Sequence`` workaround will be added in migration step 4c.
        """
        # TODO (step 4c): replace with Sequence-based PK for DuckDB:
        #
        #   pk_sequence = Sequence(f"pk_sequ_{table_name}")
        #   return Column(
        #       f"pk_{table_name}",
        #       Integer,
        #       pk_sequence,
        #       server_default=pk_sequence.next_value(),
        #       primary_key=True,
        #   )
        return super().pk_column(table_name)

    def create_schema(self, engine: Any, schema_name: str) -> None:
        """Create a schema using try/except, as required by DuckDB.

        .. note::
            This stub delegates to the base implementation. The DuckDB-specific
            try/except approach will be added in migration step 4d.
        """
        # TODO (step 4d): replace with DuckDB-specific try/except:
        #
        #   def do_create() -> None:
        #       with engine.connect() as conn:
        #           conn.execute(sqlalchemy.schema.CreateSchema(schema_name))
        #           conn.commit()
        #   try:
        #       do_create()
        #   except ProgrammingError:
        #       pass
        super().create_schema(engine, schema_name)
