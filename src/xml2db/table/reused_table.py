from hashlib import sha1

from sqlalchemy import (
    Table,
    Column,
    Integer,
    PrimaryKeyConstraint,
    UniqueConstraint,
    Boolean,
    select,
)

from .column import DataModelColumn
from .transformed_table import DataModelTableTransformed


def shorten_str(x: str, max_len: int = 30) -> str:
    if len(x) > max_len:
        h = sha1(x.encode("utf8"))
        return f"{x[:(max_len - 7)]}_{h.hexdigest()[1:6]}"
    return x


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
        d = self.data_model.dialect

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
                False,
                None,
                self.config,
                self.data_model,
            )
            yield from hash_col.get_sqlalchemy_column(temp)
            yield UniqueConstraint(
                self.data_model.model_config["record_hash_column_name"],
                name=f"{prefix if temp else ''}{shorten_str(self.name)}_xml2db_record_hash",
            )

        # build target table
        extra_args = (
            [extra for extra in self.config.get("extra_args", [])()]
            if callable(self.config.get("extra_args", []))
            else self.config.get("extra_args", [])
        )

        pk_col = d.pk_column(self.name)

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
        logical_temp_pk = f"temp_pk_{self.name}"
        self.temp_table = Table(
            d.db_identifier(f"{prefix}{self.name}"),
            self.metadata,
            Column(d.db_identifier(logical_pk), Integer, key=logical_pk),
            Column(
                d.db_identifier(logical_temp_pk),
                Integer,
                primary_key=True,
                autoincrement=False,
                key=logical_temp_pk,
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

        This method should not be called directly but through
        :meth:`~xml2db.document.Document.insert_into_target_tables`, which ensures that merge
        queries are issued in the correct order and wraps them in a transaction so that changes
        are rolled back on failure.
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
