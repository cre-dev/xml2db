from .base import DatabaseDialect


class PostgreSQLDialect(DatabaseDialect):
    """Dialect for PostgreSQL.

    PostgreSQL enforces a 63-character limit on identifiers. The
    :meth:`db_identifier` override that applies hash-suffix truncation will be
    added in migration step 5. The attribute is set here for documentation
    purposes and so tooling can query it.
    """

    MAX_IDENTIFIER_LENGTH: int = 63
