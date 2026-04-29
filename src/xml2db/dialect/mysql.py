from .base import DatabaseDialect


class MySQLDialect(DatabaseDialect):
    """Dialect for MySQL / MariaDB.

    MySQL enforces a 64-character limit on identifiers, though in practice
    the xml2db-generated names rarely exceed this. The MySQL-specific type
    mappings that currently live in ``column.py`` will be migrated into this
    class in step 3 of the migration plan.
    """

    MAX_IDENTIFIER_LENGTH: int = 64
