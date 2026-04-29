import logging
from typing import Any, TYPE_CHECKING

from sqlalchemy import Column, Integer, PrimaryKeyConstraint, Index, Sequence
from sqlalchemy.exc import ProgrammingError
from sqlalchemy import inspect as sqlalchemy_inspect
import sqlalchemy.schema

if TYPE_CHECKING:
    from ..table.column import DataModelColumn

logger = logging.getLogger(__name__)


class DatabaseDialect:
    """Encapsulates all backend-specific behaviour for xml2db.

    The base implementation provides safe, backend-agnostic defaults that work
    correctly for most SQL databases. Subclasses override only the methods that
    require backend-specific logic.

    Attributes:
        MAX_IDENTIFIER_LENGTH: Maximum number of characters allowed in a table
            or column name by this backend. Used by :meth:`db_identifier` to
            decide whether truncation is needed.
    """

    MAX_IDENTIFIER_LENGTH: int = 63  # conservative default; matches PostgreSQL

    # ------------------------------------------------------------------
    # Identifier handling
    # ------------------------------------------------------------------

    def db_identifier(self, logical_name: str) -> str:
        """Return the physical database identifier for a logical name.

        The base implementation is an identity function — it returns the name
        unchanged. Subclasses that enforce a shorter identifier limit (e.g.
        PostgreSQL's 63-character limit) should override this method to apply
        deterministic truncation.

        Args:
            logical_name: The full logical name used inside the Python model
                (e.g. ``"very_long_table_name_derived_from_xsd"``).

        Returns:
            A string that is safe to use as a database identifier for this
            backend. Guaranteed to be stable across calls with the same input.
        """
        return logical_name

    def fk_ref(self, table_logical: str, col_logical: str) -> str:
        """Return a ``"table.column"`` string using physical database names.

        This is a convenience wrapper around :meth:`db_identifier` for building
        the string argument to SQLAlchemy's ``ForeignKey(...)`` constructor,
        which requires physical names.

        Args:
            table_logical: Logical name of the referenced table.
            col_logical: Logical name of the referenced column.

        Returns:
            A ``"db_table_name.db_column_name"`` string ready for use in a
            ``ForeignKey(...)`` call.
        """
        return f"{self.db_identifier(table_logical)}.{self.db_identifier(col_logical)}"

    # ------------------------------------------------------------------
    # Column type mapping
    # ------------------------------------------------------------------

    def column_type(self, col: "DataModelColumn", temp: bool) -> Any:
        """Return the SQLAlchemy type for a given column.

        Subclasses should override this to provide backend-specific type
        mappings. The base implementation raises ``NotImplementedError`` and
        will be replaced in step 3 of the migration with the logic currently
        in ``types_mapping_default``.

        Args:
            col: The :class:`~xml2db.table.column.DataModelColumn` whose type
                is being resolved.
            temp: ``True`` when building the temporary staging table, ``False``
                for the target table. Some backends (e.g. MSSQL) use a
                different type in temp tables to work around insertion issues.

        Returns:
            A SQLAlchemy type class or instance.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not implement column_type(). "
            "This will be wired up in migration step 3."
        )

    # ------------------------------------------------------------------
    # DDL: primary key
    # ------------------------------------------------------------------

    def pk_column(self, table_name: str) -> Column:
        """Return the primary key ``Column`` for a target table.

        The base implementation uses ``autoincrement=True``, which is
        supported by all major backends. DuckDB requires a ``Sequence``-based
        workaround and overrides this method.

        Args:
            table_name: The *logical* table name, used to build the column
                name (``pk_<table_name>``). Pass the logical name here; callers
                that need the physical name for the ``Column`` constructor will
                apply :meth:`db_identifier` separately in step 7.

        Returns:
            A SQLAlchemy :class:`~sqlalchemy.Column` configured as the
            primary key.
        """
        return Column(f"pk_{table_name}", Integer, primary_key=True, autoincrement=True)

    def pk_constraint(self, table_name: str, **kwargs: Any) -> PrimaryKeyConstraint:
        """Return the ``PrimaryKeyConstraint`` for a target table.

        Extra keyword arguments are passed through to the
        ``PrimaryKeyConstraint`` constructor, allowing callers to supply
        backend-specific dialect options (e.g. ``mssql_clustered``) without
        this method needing to know about them.

        Args:
            table_name: The *logical* table name, used to build the constraint
                name (``cx_pk_<table_name>``).
            **kwargs: Additional keyword arguments forwarded to
                ``PrimaryKeyConstraint``.

        Returns:
            A :class:`~sqlalchemy.PrimaryKeyConstraint` with a deterministic
            name.
        """
        return PrimaryKeyConstraint(name=f"cx_pk_{table_name}", **kwargs)

    # ------------------------------------------------------------------
    # DDL: extra indexes
    # ------------------------------------------------------------------

    def extra_indexes(self, table_name: str, config: dict) -> list[Index]:
        """Return any backend-specific indexes to append to a table.

        The base implementation returns an empty list. The MSSQL dialect
        overrides this to return a clustered columnstore index when
        ``config["as_columnstore"]`` is ``True``.

        Args:
            table_name: The *logical* table name.
            config: The validated per-table configuration dict (as returned
                by :meth:`validate_table_config`).

        Returns:
            A (possibly empty) list of SQLAlchemy :class:`~sqlalchemy.Index`
            objects to be appended to the table via
            ``table.append_constraint(...)``.
        """
        return []

    # ------------------------------------------------------------------
    # DDL: schema management
    # ------------------------------------------------------------------

    def create_schema(self, engine: Any, schema_name: str) -> None:
        """Create a database schema if it does not already exist.

        The base implementation uses SQLAlchemy's ``inspect`` to check for
        schema existence before issuing ``CREATE SCHEMA``, which works for
        PostgreSQL, MSSQL, and MySQL. DuckDB overrides this with a
        try/except approach because its inspector does not reliably list
        schemas before they are created.

        Args:
            engine: The bound SQLAlchemy engine.
            schema_name: Name of the schema to create.
        """

        def do_create() -> None:
            with engine.connect() as conn:
                conn.execute(sqlalchemy.schema.CreateSchema(schema_name))
                conn.commit()

        inspector = sqlalchemy_inspect(engine)
        if schema_name not in inspector.get_schema_names():
            do_create()

    # ------------------------------------------------------------------
    # Config validation
    # ------------------------------------------------------------------

    def validate_table_config(self, config: dict) -> dict:
        """Strip or warn about config keys unsupported by this backend.

        The base implementation disables ``as_columnstore`` with a warning,
        since clustered columnstore indexes are an MSSQL-only feature.
        ``MSSQLDialect`` overrides this to allow the option through.

        Args:
            config: The raw per-table config dict, already parsed by
                :meth:`~xml2db.table.table.DataModelTable._validate_config`.

        Returns:
            The config dict, potentially with ``as_columnstore`` set to
            ``False``.
        """
        if config.get("as_columnstore"):
            config["as_columnstore"] = False
            logger.warning(
                "Clustered columnstore indexes are only supported with MS SQL Server database"
            )
        return config

    def validate_model_config(self, config: dict) -> dict:
        """Strip or warn about model-level config keys unsupported by this backend.

        Mirrors :meth:`validate_table_config` but operates on the top-level
        model config dict. The base implementation disables ``as_columnstore``
        with an informational log message.

        Args:
            config: The raw model-level config dict, already parsed by
                :meth:`~xml2db.model.DataModel._validate_config`.

        Returns:
            The config dict, potentially modified.
        """
        if config.get("as_columnstore"):
            config["as_columnstore"] = False
            logger.info(
                "Clustered columnstore indexes are only supported with MS SQL Server database, noop"
            )
        return config
