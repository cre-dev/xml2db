from .base import DatabaseDialect


class PostgreSQLDialect(DatabaseDialect):
    """Dialect for PostgreSQL.

    PostgreSQL enforces a 63-character limit on identifiers. Names exceeding
    this limit are truncated with a hash suffix by the base
    :meth:`~DatabaseDialect.db_identifier` implementation, which uses
    :attr:`MAX_IDENTIFIER_LENGTH` to decide when to truncate.
    """

    MAX_IDENTIFIER_LENGTH: int = 63
