from sqlalchemy import (
    Table,
    Column,
    Integer,
    Index,
    PrimaryKeyConstraint,
    UniqueConstraint,
    Boolean,
    select,
    Sequence,
)

from .transformed_table import DataModelTableTransformed
from .column import DataModelColumn


class DataModelTableReused(DataModelTableTransformed):
    """A table data model which de-duplicates records in the database based on their hash value.

    This table model is the default model to store XML nodes. n-n relationships with parent nodes \
    are represented with an intermediate relationship table. Although more complicated than the \
    duplicated version, this table model store less records in the database.
    """

    is_reused = True

    def build_sqlalchemy_tables(self):
        """Build sqlalchemy table objects.

        Build the sqlalchemy table objet based on table attributes for the main table, \
        and relation tables to store n-n relationships, for target and temp tables \
        (so it builds at least 2 tables if there is no relations).
        This method is intended to be called only once (if it called more than once it \
        will return immediately) and further changes to the table will not be updated.

        """

        if self.table is not None:
            return

        prefix = f"temp_{self.temp_prefix}_"

        # build target table and n-n relations tables
        def get_col(temp=False):
            for field_type, key, field in self.fields:
                if field_type == "col" or field_type == "rel1":
                    yield from field.get_sqlalchemy_column(temp)
            # Root table is given additional integration metadata columns
            if (
                self.is_root_table
                and "metadata_columns" in self.data_model.model_config
            ):
                for metadata_col in self.data_model.model_config["metadata_columns"]:
                    yield Column(
                        metadata_col["name"],
                        metadata_col["type"],
                        **{
                            k: v
                            for k, v in metadata_col.items()
                            if k not in ["name", "type"]
                        },
                    )
            # Use DataModelColumn to create record hash column in order to get the right data type
            hash_col = DataModelColumn(
                self.data_model.model_config["record_hash_column_name"],
                [],
                "binary",
                [1, 1],
                self.data_model.model_config["record_hash_size"],
                self.data_model.model_config["record_hash_size"],
                False,
                False,
                False,
                None,
                self.config,
                self.data_model,
            )
            yield from hash_col.get_sqlalchemy_column(temp)
            yield UniqueConstraint(
                self.data_model.model_config["record_hash_column_name"],
                name=f"{prefix if temp else ''}{self.name}_xml2db_record_hash",
            )

        # build target table
        extra_args = (
            [extra for extra in self.config.get("extra_args", [])()]
            if callable(self.config.get("extra_args", []))
            else self.config.get("extra_args", [])
        )

        if self.data_model.db_type == "duckdb":
            pk_sequence = Sequence(f"pk_sequ_{self.name}")
            pk_col = Column(
                f"pk_{self.name}",
                Integer,
                pk_sequence,
                server_default=pk_sequence.next_value(),
                primary_key=True,
            )
        else:
            pk_col = Column(
                f"pk_{self.name}", Integer, primary_key=True, autoincrement=True
            )

        self.table = Table(
            self.name,
            self.metadata,
            pk_col,
            PrimaryKeyConstraint(
                name=f"cx_pk_{self.name}",
                mssql_clustered=not self.config["as_columnstore"],
            ),
            *get_col(),
            *extra_args,
        )

        # set columnstore index
        if self.config["as_columnstore"]:
            self.table.append_constraint(
                Index(
                    f"idx_{self.name}_columnstore",
                    mssql_clustered=True,
                    mssql_columnstore=True,
                )
            )

        # build temporary table
        self.temp_table = Table(
            f"{prefix}{self.name}",
            self.metadata,
            Column(f"pk_{self.name}", Integer),
            Column(
                f"temp_pk_{self.name}", Integer, primary_key=True, autoincrement=False
            ),
            *get_col(temp=True),
            Column("temp_exists", Boolean, default=False),
        )

        # build relation tables
        for rel in self.relations_n.values():
            rel.build_relation_tables()

        self._set_db_schema()

    def get_merge_temp_records_statements(self):
        """Yield insert and update statements to merge temporary tables into target tables

        This method yield SQL statements inserting the data of the temporary table (prefixed)
        into the target tables (unprefixed). It deals with primary keys and foreign keys by
        looking up first existing records with the same hash in order to reuse already existing
        records when the new record is identical.

        This method should not be called directly but through the save_db method in the Document
        class, which will ensure that merge queries are issued in the correct order for all the
        data flow, and which will encapsulated all queries in a transaction in order to rollback
        changes on failure.
        """

        # find matching records hash in target table
        yield self.temp_table.update().values(temp_exists=True).where(
            getattr(
                self.temp_table.c,
                self.data_model.model_config["record_hash_column_name"],
            )  # noqa: Linter puzzled by ==
            == getattr(
                self.table.c, self.data_model.model_config["record_hash_column_name"]
            )
        )

        # update foreign keys for n-1 relations tables
        for rel in self.relations_1.values():
            yield from rel.get_merge_temp_records_statements()

        # insert missing records from temp table to target
        cols = [
            col_name
            for col_name in self.temp_table.columns.keys()
            if not col_name.startswith("temp_") and col_name != f"pk_{self.name}"
        ]
        sel = select(*[getattr(self.temp_table.c, col) for col in cols]).where(
            self.temp_table.c.temp_exists
            == False  # noqa: SQLAlchemy not supporting "is False"
        )
        yield self.table.insert().from_select(cols, sel)

        # update primary keys back in temp table
        yield self.temp_table.update().values(
            **{f"pk_{self.name}": getattr(self.table.c, f"pk_{self.name}")}
        ).where(
            getattr(
                self.temp_table.c,
                self.data_model.model_config["record_hash_column_name"],
            )  # noqa: Linter puzzled by ==
            == getattr(
                self.table.c, self.data_model.model_config["record_hash_column_name"]
            )
        )

        # update primary keys for n-n relations tables
        for rel in self.relations_n.values():
            yield from rel.get_merge_temp_records_statements()
