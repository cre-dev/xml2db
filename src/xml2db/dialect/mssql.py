from .base import DatabaseDialect


class MSSQLDialect(DatabaseDialect):
    """Dialect for Microsoft SQL Server.

    MSSQL supports identifiers up to 128 characters, so no truncation is
    needed. The columnstore index support and MSSQL-specific type mappings
    that currently live in ``column.py``, ``duplicated_table.py``,
    ``reused_table.py``, and ``relations.py`` will be migrated into this class
    in steps 3 and 4 of the migration plan.
    """

    MAX_IDENTIFIER_LENGTH: int = 128

    def validate_table_config(self, config: dict) -> dict:
        """Allow ``as_columnstore`` through unchanged for MSSQL."""
        return config

    def validate_model_config(self, config: dict) -> dict:
        """Allow ``as_columnstore`` through unchanged for MSSQL."""
        return config
