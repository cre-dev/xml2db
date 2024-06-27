from typing import Iterable, List, Any, Union, TYPE_CHECKING
import logging
import sqlalchemy
from sqlalchemy import Table
from sqlalchemy.schema import CreateTable, CreateIndex

from .column import DataModelColumn
from .relations import DataModelRelation1, DataModelRelationN
from ..exceptions import DataModelConfigError, check_type

if TYPE_CHECKING:
    from ..model import DataModel

logger = logging.getLogger(__name__)


class DataModelTable:
    """A class representing a database table translated from an XML schema complex type

    Args:
        table_name: the table's name
        type_name: the XSD complex type name
        is_root_table: is this table the root table?
        is_virtual_node: was this table created to store multiple root elements?
        metadata: :class:`sqlalchemy.Metadata` object to build sqlalchemy models into
        config: model's configuration
        db_schema: database schema to use
        temp_prefix: temp prefix to use for naming temp tables
        data_model: the `DataModel` instance

    Attributes:
        model_group: 'choice' or 'sequence', extracted from the XSD. 'choice' means that only one field can have a
            value at the same time
        is_root_table: is this table the root table?
        fields: a list of tuples describing all table fields, ordered, in the form (type, name, object) where type can
            be "col", "rel1" or "reln", name is the name of the column or relation, and object is the column
            or relationship object
        columns: a dict of all columns (fields with simple values), keyed by field name
        relations_1: a dict of 0-1 or 1-1 relations, keyed by field name
        relations_n: a dict of 0-n or 1-n relations, keyed by field name
    """

    is_reused = None

    def __init__(
        self,
        table_name: str,
        type_name: str,
        is_root_table: bool,
        is_virtual_node: bool,
        metadata: sqlalchemy.MetaData,
        config: dict,
        db_schema: str,
        temp_prefix: str,
        data_model: "DataModel",
    ):
        """Constructor method"""

        # config attributes
        self.name = table_name
        self.type_name = type_name
        self.is_root_table = is_root_table
        self.is_virtual_node = is_virtual_node
        self.model_group = "sequence"
        self.config = self._validate_config(config, data_model.db_type)
        self.db_schema = db_schema
        self.temp_prefix = temp_prefix

        # fields (columns and relations)
        self.fields = []
        self.columns = {}
        self.relations_1 = {}
        self.relations_n = {}

        # dependencies logic
        self.is_simplified = False  # is the table already simplified ? (used in the simplification process)
        self.parents_1 = (
            set()
        )  # a set of 1-1 relations the table is involved in as a child
        self.parents_n = (
            set()
        )  # a set of 1-n relations the table is involved in as a child
        self.parent = None
        self.dependencies = (
            set()
        )  # a set of tables this table depends on (can be children or parents)
        self.referenced_as_fk = False

        # sqlalchemy objects
        self.metadata = metadata
        self.table = None
        self.temp_table = None
        self.data_model = data_model

    def _validate_config(self, cfg, db_type):
        if cfg is None:
            cfg = {}

        config = {
            "reuse": check_type(cfg, "reuse", bool, True),
            "as_columnstore": check_type(cfg, "as_columnstore", bool, False),
        }
        if "extra_args" in cfg and not (
            isinstance(cfg["extra_args"], list)
            or isinstance(cfg["extra_args"], tuple)
            or callable(cfg["extra_args"])
        ):
            raise DataModelConfigError("extra_args must be a list, a tuple or callable")
        config["extra_args"] = cfg.get("extra_args", [])
        if "choice_transform" in cfg:
            config["choice_transform"] = check_type(
                cfg, "choice_transform", bool, False
            )

        if config["as_columnstore"] and not db_type == "mssql":
            config["as_columnstore"] = False
            logger.warning(
                "Clustered columnstore indexes are only supported with MS SQL Server database"
            )

        config["fields"] = cfg.get("fields", {})

        return config

    def add_column(
        self,
        name: str,
        data_type: str,
        occurs: List[int],
        min_length: int,
        max_length: Union[int, None],
        is_attr: bool,
        is_content: bool,
        allow_empty: bool,
        ngroup: Union[str, None],
    ) -> None:
        """Helper to add a new column to the model

        Args:
            name: name of the column
            data_type: data type
            occurs: min and max occurrences
            min_length: minimum length
            max_length: maximum length
            is_attr: is XML attribute or element?
            is_content: is content of a mixed type element?
            allow_empty: is nullable?
            ngroup: a string id signaling that the column belongs to a nested sequence
        """
        self.columns[name] = DataModelColumn(
            name,
            [(name, None)],
            data_type,
            occurs,
            min_length,
            max_length,
            is_attr,
            is_content,
            allow_empty,
            ngroup,
            self.config,
            self.data_model,
        )
        self.fields.append(("col", name, self.columns[name]))

    def add_relation_1(
        self,
        name: str,
        other_table: "DataModelTable",
        occurs: List[int],
        ngroup: Union[str, None],
    ) -> None:
        """Helper to add a 1-to-1 relationship

        Args:
            name: name of the 1-1 relationship
            other_table: the child table of the relationship
            occurs: min and max occurs for this relationship
            ngroup: a string id signaling that the relation belongs to a nested sequence
        """
        if occurs[1] != 1:
            raise ValueError(
                "attempting to add a 1-1 relationship with max occurrences different from 1"
            )
        rel = DataModelRelation1(
            name,
            [(name, other_table.type_name)],
            self,
            other_table,
            occurs,
            ngroup,
            self.data_model,
        )
        self.relations_1[name] = rel
        self.fields.append(("rel1", name, rel))
        other_table.parents_1.add(rel)

    def add_relation_n(self, name, other_table, occurs, ngroup):
        """Helper to add a 1-to-many relationship

        Args:
            name: name of the 1-1 relationship
            other_table: the child table of the relationship
            occurs: min and max occurs for this relationship
            ngroup: a string id signaling that the relation belongs to a nested sequence
        """
        if occurs[1] == 1:
            raise ValueError(
                "attempting to add a 1-n relationship with max occurrences equal to 1"
            )
        rel = DataModelRelationN(
            name,
            [(name, other_table.type_name)],
            self,
            other_table,
            occurs,
            ngroup,
            self.data_model,
        )
        self.relations_n[name] = rel
        self.fields.append(("reln", name, rel))
        other_table.parents_n.add(rel)

    def compute_dependencies(self) -> None:
        """Compute the table's dependencies according to foreign keys relationships.

        Dependencies are tables that the current table holds foreign keys relationships to (i.e. the one which need
        to exist before this one can be created, for instance). To compute `dependencies` list, it ignores fk referenced
        in relationship tables for n-n relationships. For `referenced_as_fk` it is more litteral and include those.

        This function should be called after schema simplification because dependencies will not \
        be properly updated during the simplification process.
        """
        # we drop parents information which is no longer accurate after schema simplification
        self.parents_1 = None
        self.parents_n = None
        for field_type, rel_name, relation in self.fields:
            if field_type == "rel1" or field_type == "reln":
                if (
                    relation.other_table.parent is not None
                    and not relation.other_table.is_reused
                ):
                    raise ValueError(
                        f"unsupported: table {relation.other_table.name} is not reused and has more than 1 parent"
                    )
                relation.other_table.parent = self
                if relation.other_table.is_reused:
                    self.dependencies.add(relation.other_table.type_name)
                    relation.other_table.referenced_as_fk = True
                    if (
                        field_type == "reln"
                    ):  # the relationship table will create a fk constraint to self
                        self.referenced_as_fk = True
                else:
                    relation.other_table.dependencies.add(self.type_name)
                    self.referenced_as_fk = True

    def _set_db_schema(self) -> None:
        """Set db schema value for sqlalchemy tables objects"""
        if (
            self.db_schema is not None
            and self.table is not None
            and self.temp_table is not None
        ):
            # sqlalchemy.Table.schema is the db_schema
            self.table.schema = self.db_schema
            self.temp_table.schema = self.db_schema

    def get_create_table_statements(self, temp=False) -> Iterable[CreateTable]:
        """Yield create table statements for the table and the rel tables

        Args:
            temp: if True, yield create table statements for temporary tables (prefixed)
        """
        if temp:
            yield CreateTable(self.temp_table)
            for relation in self.relations_n.values():
                if relation.temp_rel_table is not None:
                    yield CreateTable(relation.temp_rel_table)
        else:
            yield CreateTable(self.table)
            for relation in self.relations_n.values():
                if relation.rel_table is not None:
                    yield CreateTable(relation.rel_table)

    def get_create_index_statements(self) -> Iterable[CreateIndex]:
        """Yield create index statements for the indexes of the table and its relation tables"""

        def yield_indexes(table: Table) -> Iterable[CreateIndex]:
            indexes = [index for index in table.indexes]
            # Sort to guarantee indexes statements of a same table are printed in the same order everytime, otherwise
            # the order is random, and it may create useless git changes in the output folder
            indexes.sort(key=lambda index: index.name)
            for index in indexes:
                yield CreateIndex(index)

        yield from yield_indexes(self.table)

        for relation in self.relations_n.values():
            if relation.rel_table is not None:
                yield from yield_indexes(relation.rel_table)

    def create_tables(self, engine: sqlalchemy.engine.base.Engine, temp: bool = False):
        """Create tables, either target tables or temp tables used to import data

        Args:
            engine: a sqlalchemy engine to use
            temp: if True, create temporary (prefixed) tables
        """
        if temp:
            self.temp_table.create(engine, checkfirst=True)
        else:
            self.table.create(engine, checkfirst=True)
        for relation in self.relations_n.values():
            relation.create_table(engine, temp)

    def get_insert_temp_records_statements(
        self, data: Union[dict, None]
    ) -> Iterable[Any]:
        """Yield drop table if exists, create table and insert statement for temporary tables"""
        if data is not None and len(data["records"]) > 0:
            yield self.temp_table.insert(), data["records"]
            data_rel = data.get("relations_n", {})
            for relation in self.relations_n.values():
                if (
                    relation.rel_table_name in data_rel
                    and len(data_rel[relation.rel_table_name]["records"]) > 0
                ):
                    yield relation.temp_rel_table.insert(), data_rel[
                        relation.rel_table_name
                    ]["records"]

    def drop_tables(self, engine: sqlalchemy.engine.base.Engine) -> None:
        """Drop target (unprefixed) tables (main table and relations)

        BE CAUTIOUS, THIS METHOD DROPS TABLES WITHOUT FURTHER NOTICE!

        Args:
            engine: a sqlalchemy engine to use
        """
        for rel in self.relations_n.values():
            if rel.rel_table is not None:
                rel.rel_table.drop(engine, checkfirst=True)
        self.table.drop(engine, checkfirst=True)

    def drop_temp_tables(self, engine: sqlalchemy.engine.base.Engine) -> None:
        """Drop temporary (prefixed) tables (main table and relations)

        BE CAUTIOUS, THIS METHOD DROPS TABLES WITHOUT FURTHER NOTICE!

        Args:
            engine: a sqlalchemy engine to use
        """
        for rel in self.relations_n.values():
            if rel.temp_rel_table is not None:
                rel.temp_rel_table.drop(engine, checkfirst=True)
        self.temp_table.drop(engine, checkfirst=True)

    def get_entity_rel_diagram(self) -> List:
        """Build ERD representation for a single table and its relationships

        The string representation is used by mermaid.js to create a visual diagram.

        Returns:
            a list of strings (lines)
        """
        out = (
            [
                f"{self.name} ||--{'o' if rel.occurs[0] == 0 else '|'}| {rel.other_table.name} : "
                f'"{rel.name}"'
                for rel in self.relations_1.values()
            ]
            + [
                f"{self.name} ||--{'o' if rel.occurs[0] == 0 else '|'}{{ {rel.other_table.name} : "
                f"\"{rel.name}{'*' if rel.other_table.is_reused else ''}\""
                for rel in self.relations_n.values()
            ]
            + [f"{self.name} {{"]
            + [
                (
                    f"    {self.columns[field[1]].data_type}{'-N' if self.columns[field[1]].occurs[1] is None else ''} "
                    f"{field[1].replace('.', '_')}"
                )
                for field in self.fields
                if field[0] == "col"
            ]
            + ["}"]
        )
        return [f"    {line}" for line in out]
