import sqlalchemy.engine
from sqlalchemy import Table, Column, ForeignKey, Integer, Index, select
from typing import TYPE_CHECKING, List, Iterable, Any, Union

if TYPE_CHECKING:
    from .table import DataModelTable
    from .. import DataModel


class DataModelRelation:
    """A class representing a relation with another table

    Args:
        name: the name of the field holding the relation in the parent table
        name_chain: a list of field names accounting for elevated fields
        table: the parent table model in the relation
        other_table: the other table model in the relation
        occurs: list of int with two elements: min occurrences and max occurrences. Max occurrences is None if
            unbounded
        ngroup: a key used to handle nested sequences
        data_model: the DataModel object it belongs to
    """

    def __init__(
        self,
        name: str,
        name_chain: list,
        table: "DataModelTable",
        other_table: "DataModelTable",
        occurs: List[int],
        ngroup: Union[str, None],
        data_model: "DataModel",
    ):
        """Constructor method"""
        self.name = name
        self.name_chain = name_chain
        self.table = table
        self.other_table = other_table
        self.occurs = occurs
        self.ngroup = ngroup
        self.rel_table_name = None
        self.field_name = None
        self.rel_table = None
        self.temp_rel_table = None
        self.data_model = data_model


class DataModelRelation1(DataModelRelation):
    """A class representing a 1-1 relation with another table"""

    def get_sqlalchemy_column(self, temp: bool = False):
        """Yields SQLAlchemy object representing the foreign key relation

        Args:
            temp: are we targeting temp or target table?
        """
        self.field_name = (
            f"{self.name}_fk_{self.other_table.name}"
            if not self.name.endswith(self.other_table.name)
            else f"fk_{self.name}"
        )
        if temp:
            yield Column(f"temp_{self.field_name}", Integer)
            yield Column(self.field_name, Integer)
        else:
            yield Column(
                self.field_name,
                Integer,
                ForeignKey(f"{self.other_table.name}.pk_{self.other_table.name}"),
            )

    def get_merge_temp_records_statements(self) -> Iterable[Any]:
        """A SQL statement to update foreign keys values from target table back to temp table after insert

        Returns:
            an iterable of SQL statements
        """
        yield self.table.temp_table.update().values(
            **{
                self.field_name: getattr(
                    self.other_table.temp_table.c, f"pk_{self.other_table.name}"
                )
            }
        ).where(
            getattr(self.table.temp_table.c, f"temp_{self.field_name}")
            == getattr(
                self.other_table.temp_table.c, f"temp_pk_{self.other_table.name}"
            )
        )


class DataModelRelationN(DataModelRelation):
    """A class representing a 1-N relation with another table"""

    def build_relation_tables(self) -> None:
        """Builds sqlalchemy objects for intermediate relationship tables"""
        self.rel_table_name = (
            f"{self.table.name}_{self.name}_{self.other_table.name}"
            if not self.name.endswith(self.other_table.name)
            else f"{self.table.name}_{self.name}"
        )
        prefix = f"temp_{self.table.temp_prefix}_"
        if self.other_table.is_reused:
            self.temp_rel_table = Table(
                f"{prefix}{self.rel_table_name}",
                self.table.metadata,
                Column(f"temp_fk_{self.table.name}", Integer, nullable=False),
                Column(f"fk_{self.table.name}", Integer),
                Column(f"temp_fk_{self.other_table.name}", Integer, nullable=False),
                Column(f"fk_{self.other_table.name}", Integer),
                *(
                    (
                        Column(
                            "xml2db_row_number",
                            Integer,
                            nullable=False,
                        ),
                    )
                    if self.data_model.model_config["row_numbers"]
                    else ()
                ),
            )
            cl_index = tuple()
            if self.data_model.db_type == "mssql":
                # n-n relation tables don't have a primary key, so we define a clustered index on the first FK
                cl_index = (
                    Index(
                        f"ix_fk_{self.rel_table_name}",
                        f"fk_{self.table.name}",
                        f"fk_{self.other_table.name}",
                        mssql_clustered=True,
                    ),
                )

            self.rel_table = Table(
                self.rel_table_name,
                self.table.metadata,
                Column(
                    f"fk_{self.table.name}",
                    Integer,
                    ForeignKey(f"{self.table.name}.pk_{self.table.name}"),
                    nullable=False,
                    index=(cl_index == tuple()),
                ),
                Column(
                    f"fk_{self.other_table.name}",
                    Integer,
                    ForeignKey(f"{self.other_table.name}.pk_{self.other_table.name}"),
                    nullable=False,
                    index=True,
                ),
                *(
                    (
                        Column(
                            "xml2db_row_number",
                            Integer,
                            nullable=False,
                        ),
                    )
                    if self.data_model.model_config["row_numbers"]
                    else ()
                ),
                *cl_index,
            )

            if self.table.db_schema is not None:
                self.rel_table.schema = self.table.db_schema
                self.temp_rel_table.schema = self.table.db_schema

    def create_table(
        self, engine: sqlalchemy.engine.Engine, temp: bool = False
    ) -> None:
        """Create intermediate relationship table

        Args:
            engine: sqlalchemy engine to use
            temp: are we creating temp or target table?
        """
        if temp:
            if self.temp_rel_table is not None:
                self.temp_rel_table.create(engine, checkfirst=True)
        else:
            if self.rel_table is not None:
                self.rel_table.create(engine, checkfirst=True)

    def get_merge_temp_records_statements(self) -> Iterable[Any]:
        """Issue SQL statements to insert new records in the intermediate relationship table

        First, it will update foreign keys in the relationship table to use target tables foreign keys.
        Then, it will insert new relationship records into the target relationship table

        Returns:
            sqlalchemy query statements
        """
        if self.other_table.is_reused:
            rel_tb = self.temp_rel_table
            # update foreign key with self
            yield rel_tb.update().values(
                **{
                    f"fk_{self.table.name}": getattr(
                        self.table.temp_table.c, f"pk_{self.table.name}"
                    )
                }
            ).where(
                getattr(  # noqa: Linter puzzled by ==
                    rel_tb.c, f"temp_fk_{self.table.name}"
                )
                == getattr(self.table.temp_table.c, f"temp_pk_{self.table.name}")
            ).where(
                self.table.temp_table.c.temp_exists
                == False  # noqa: SQLAlchemy not supporting "is False"
            )
            # update foreign key with other table
            yield rel_tb.update().values(
                **{
                    f"fk_{self.other_table.name}": getattr(
                        self.other_table.temp_table.c, f"pk_{self.other_table.name}"
                    )
                }
            ).where(
                getattr(  # noqa: Linter puzzled by ==
                    rel_tb.c, f"temp_fk_{self.other_table.name}"
                )
                == getattr(
                    self.other_table.temp_table.c, f"temp_pk_{self.other_table.name}"
                )
            )
            # insert new records
            cols = [f"fk_{self.table.name}", f"fk_{self.other_table.name}"]
            if self.data_model.model_config["row_numbers"]:
                cols = cols + ["xml2db_row_number"]
            sel = select(*[getattr(rel_tb.c, col) for col in cols]).where(
                getattr(rel_tb.c, f"fk_{self.table.name}")  # noqa
                != None  # SQLAlchemy not supporting "is not None"
            )
            yield self.rel_table.insert().from_select(cols, sel)
