from typing import Iterable, Any
from sqlalchemy import (
    Table,
    Column,
    Integer,
    ForeignKey,
    PrimaryKeyConstraint,
    Boolean,
    select,
    and_,
)

from .transformed_table import DataModelTableTransformed


class DataModelTableDuplicated(DataModelTableTransformed):
    """A table data model which allows duplicated records in the database.

    This table model is only allowed if this node type is used only once in the schema, in a 1-n relationship with
    its parent node. The 1-n relationship is represented with a foreign key relation from this node to its parent node,
    without intermediate relationship table. As such, it is a simpler schema, with the drawback of having duplicates
    records.
    """

    is_reused = False

    def build_sqlalchemy_tables(self) -> None:
        """Build sqlalchemy table objects.

        Build the sqlalchemy table objet based on table attributes for the main table, and relation tables to store n-n
        relationships with children nodes, for target and temp tables (so it builds at least 2 tables if there is no
        relations).

        This method is intended to be called only once (if it called more than once it will return immediately) and
        further changes to the table will not be updated.
        """

        if self.table is not None:
            return

        prefix = f"temp_{self.temp_prefix}_"
        d = self.data_model.dialect

        def get_col(temp=False) -> Iterable[Column]:
            """Generator function to build sqlalchemy Column objects

            Args:
                temp: are we targeting temp or target table?
            """

            # temp primary key which is used also in the final table to update back target pk
            if temp or self.referenced_as_fk:
                logical = f"temp_pk_{self.name}"
                yield Column(
                    d.db_identifier(logical),
                    Integer,
                    primary_key=temp,
                    autoincrement=False,
                    key=logical,
                )
            # foreign key column to link with parent
            if temp:
                logical_tmp = f"temp_fk_parent_{self.parent.name}"
                yield Column(d.db_identifier(logical_tmp), Integer, key=logical_tmp)
                logical_fk = f"fk_parent_{self.parent.name}"
                yield Column(d.db_identifier(logical_fk), Integer, key=logical_fk)
            else:
                logical_fk = f"fk_parent_{self.parent.name}"
                yield Column(
                    d.db_identifier(logical_fk),
                    Integer,
                    ForeignKey(d.fk_ref(self.parent.name, f"pk_{self.parent.name}")),
                    key=logical_fk,
                )
            # row_number if needed
            if self.data_model.model_config["row_numbers"]:
                yield Column(
                    "xml2db_row_number",
                    Integer,
                    nullable=False,
                )
            # all other columns and 1-1 relationships
            for field_type, key, field in self.fields:
                if field_type == "col" or field_type == "rel1":
                    yield from field.get_sqlalchemy_column(temp)

        # build target table
        extra_args = (
            [extra for extra in self.config.get("extra_args", [])()]
            if callable(self.config.get("extra_args", []))
            else self.config.get("extra_args", [])
        )
        pk_col = self.data_model.dialect.pk_column(self.name)
        self.table = Table(
            d.db_identifier(self.name),
            self.metadata,
            pk_col,
            PrimaryKeyConstraint(
                name=d.db_identifier(f"cx_pk_{self.name}"),
                mssql_clustered=not self.config["as_columnstore"],
            ),
            *get_col(),
            *extra_args,
        )

        # set backend-specific extra indexes (e.g. columnstore)
        for idx in self.data_model.dialect.extra_indexes(self.name, self.config):
            self.table.append_constraint(idx)

        # build temporary table
        logical_pk = f"pk_{self.name}"
        self.temp_table = Table(
            d.db_identifier(f"{prefix}{self.name}"),
            self.metadata,
            Column(d.db_identifier(logical_pk), Integer, key=logical_pk),
            *get_col(temp=True),
            Column("temp_exists", Boolean, default=False),
        )

        # build relationship tables
        for rel in self.relations_n.values():
            rel.build_relation_tables()

        self._set_db_schema()

    def get_merge_temp_records_statements(self) -> Iterable[Any]:
        """Yield insert and update statements to merge temporary tables into target tables

        This method yields SQL statements inserting the data of the temporary table (prefixed) \
        into the target tables (unprefixed). As this kind of node can be duplicated, no unique constraint \
        is used, but a record is inserted only if its parent record is inserted too.

        This method should not be called directly but through
        :meth:`~xml2db.document.Document.insert_into_target_tables`, which ensures that merge
        queries are issued in the correct order and wraps them in a transaction so that changes
        are rolled back on failure.
        """

        # update foreign keys and temp_exists based on parent table
        yield self.temp_table.update().values(
            **{
                f"fk_parent_{self.parent.name}": getattr(
                    self.parent.temp_table.c, f"pk_{self.parent.name}"
                ),
                "temp_exists": self.parent.temp_table.c.temp_exists,
            }
        ).where(
            getattr(self.temp_table.c, f"temp_fk_parent_{self.parent.name}")  # noqa
            == getattr(self.parent.temp_table.c, f"temp_pk_{self.parent.name}")
        )

        # update foreign keys for n-1 relations tables
        for rel in self.relations_1.values():
            yield from rel.get_merge_temp_records_statements()

        # insert new records from temp table to target
        cols = [
            col_name
            for col_name in self.table.columns.keys()
            if col_name != f"pk_{self.name}"
        ]
        sel = select(*[getattr(self.temp_table.c, col) for col in cols]).where(
            self.temp_table.c.temp_exists
            == False  # noqa: SQLAlchemy not supporting "is False"
        )
        yield self.table.insert().from_select(cols, sel)

        # if table is referenced in a fk relationship, update primary keys back in temp table
        if self.referenced_as_fk:
            yield self.temp_table.update().values(
                **{f"pk_{self.name}": getattr(self.table.c, f"pk_{self.name}")}
            ).where(
                and_(
                    getattr(self.temp_table.c, f"fk_parent_{self.parent.name}")
                    == getattr(self.table.c, f"fk_parent_{self.parent.name}"),
                    getattr(self.temp_table.c, f"temp_pk_{self.name}")
                    == getattr(self.table.c, f"temp_pk_{self.name}"),
                )
            )

        # update records for n-n relations tables
        for rel in self.relations_n.values():
            yield from rel.get_merge_temp_records_statements()
