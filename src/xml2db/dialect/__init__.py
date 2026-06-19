"""Backend-specific dialect classes for xml2db.

This package centralises all database-backend-specific behaviour that was
previously scattered across the codebase as ``if db_type == "..."``
conditionals. Each supported backend has a dedicated subclass of
:class:`~xml2db.dialect.base.DatabaseDialect`. Unknown backends fall back to
the base class, which provides safe, generic defaults.

Usage::

    from xml2db.dialect import get_dialect

    dialect = get_dialect("postgresql")
    physical_name = dialect.db_identifier("some_very_long_xsd_derived_name")

The registry is a plain dict so that third-party code (or tests) can register
custom dialects without subclassing anything in xml2db::

    from xml2db.dialect import DIALECT_REGISTRY
    from mypackage import OracleDialect

    DIALECT_REGISTRY["oracle"] = OracleDialect
"""

from .base import DatabaseDialect
from .duckdb import DuckDBDialect
from .mssql import MSSQLDialect
from .mysql import MySQLDialect
from .postgresql import PostgreSQLDialect

__all__ = [
    "DatabaseDialect",
    "DuckDBDialect",
    "MSSQLDialect",
    "MySQLDialect",
    "PostgreSQLDialect",
    "DIALECT_REGISTRY",
    "get_dialect",
]

# Maps the SQLAlchemy dialect name (as returned by engine.dialect.name) to
# the corresponding DatabaseDialect subclass.
DIALECT_REGISTRY: dict[str, type[DatabaseDialect]] = {
    "postgresql": PostgreSQLDialect,
    "mssql": MSSQLDialect,
    "mysql": MySQLDialect,
    "mariadb": MySQLDialect,  # SQLAlchemy reports MariaDB as "mariadb"
    "duckdb": DuckDBDialect,
}


def get_dialect(db_type: str | None, **kwargs) -> DatabaseDialect:
    """Return a :class:`DatabaseDialect` instance for the given backend name.

    Args:
        db_type: The SQLAlchemy dialect name, e.g. ``"postgresql"``,
            ``"mssql"``, ``"mysql"``, ``"duckdb"``. ``None`` or any
            unrecognised string falls back to the base
            :class:`DatabaseDialect`, which uses safe generic defaults.
        **kwargs: Extra keyword arguments forwarded to the dialect constructor.
            Unknown kwargs are silently ignored by subclasses that do not
            declare them.

    Returns:
        An instantiated :class:`DatabaseDialect` (or subclass) ready for use.
    """
    cls = DIALECT_REGISTRY.get(db_type, DatabaseDialect)
    return cls(**kwargs)
