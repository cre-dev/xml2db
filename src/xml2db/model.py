import logging
import os
from datetime import datetime
from io import BytesIO
from typing import Iterable, Union
from uuid import uuid4

import xmlschema
import sqlalchemy
from sqlalchemy import MetaData, create_engine, inspect
from sqlalchemy.sql.ddl import CreateIndex, CreateTable
from graphlib import TopologicalSorter

from xml2db import document
from xml2db.exceptions import DataModelConfigError
from xml2db.table import (
    DataModelTableReused,
    DataModelTableDuplicated,
)
from xml2db.xml_converter import XMLConverter

logger = logging.getLogger(__name__)


class DataModel:
    """A class to manage a data model based on an XML schema and its database equivalent.

    This class allows parsing a set of XSD files to build  a representation of
    the XML schema, simplify it and convert it into a set of database tables.
    It also allows parsing XML documents that fit this XML schema in order to import
    the data into the database.

    :param xsd_file: A path to a XSD file
    :param short_name: A short name for the schema
    :param long_name: A longer name for the schema
    :param base_url: The root folder to find other dependant XSD files (by default, the location of the \
    provided XSD file)
    :param model_config: A config dict to provide options for building the model
    :param connection_string: A database connection string (optional if you will not be loading data)
    :param db_type: The targeted database backend (postgresql, mssql, mysql...). It is ignored and inferred from \
    `connection_string`, if provided
    :param db_schema: A schema name to use in the database
    :param temp_prefix: A prefix to use for temporary tables (if `None`, will be generated randomly)

    :ivar xml_schema: The `xmlschema.XMLSchema` object associated with this data model
    :ivar data_flow_name: A short identifier used for the data model (`short_name` argument value)
    :ivar data_flow_long_name: A longer for the data model (`long_name` argument value)
    :ivar db_schema: A database schema name to store the database tables
    :ivar source_tree: A text representation of the source data model tree
    :ivar target_tree: A text representation of the simplified data model tree \
    which will be used to create target tables
    """

    def __init__(
        self,
        xsd_file: str,
        short_name: str = None,
        long_name: str = None,
        base_url: str = None,
        model_config: dict = None,
        connection_string: str = None,
        db_type: str = None,
        db_schema: str = None,
        temp_prefix: str = None,
    ):
        self.xml_schema = xmlschema.XMLSchema(
            os.path.basename(xsd_file) if base_url is None else xsd_file,
            base_url=(
                base_url
                if base_url is not None
                else os.path.normpath(os.path.dirname(xsd_file))
            ),
        )
        self.xml_converter = XMLConverter(data_model=self)
        self.data_flow_name = short_name
        self.data_flow_long_name = long_name

        if connection_string is None:
            logger.warning(
                "DataModel created without connection string cannot do actual imports"
            )
            self.engine = None
            self.db_type = db_type
        else:
            engine_options = {}
            if "mssql" in connection_string:
                engine_options = {
                    "fast_executemany": True,
                }
            self.engine = create_engine(
                connection_string,
                isolation_level="SERIALIZABLE",
                **engine_options,
            )
            self.db_type = self.engine.dialect.name

        self.model_config = {} if model_config is None else model_config

        # validate row_numbers global option value
        if "row_numbers" in self.model_config:
            if not isinstance(self.model_config["row_numbers"], bool):
                raise DataModelConfigError("row_numbers must be a bool")
        else:
            self.model_config["row_numbers"] = False

        # as_columnstore global option available only for MSSQL database
        if "as_columnstore" in self.model_config:
            if not isinstance(self.model_config["as_columnstore"], bool):
                raise DataModelConfigError("as_columnstore must be a bool")
            if (
                self.model_config["as_columnstore"]
                and self.engine
                and not self.engine.dialect.name == "mssql"
            ):
                self.model_config["as_columnstore"] = False
                logger.info(
                    "Clustered columnstore indexes are only supported with MS SQL Server database, noop"
                )
        else:
            self.model_config["as_columnstore"] = False

        self.db_schema = db_schema
        self.temp_prefix = str(uuid4())[:8] if temp_prefix is None else temp_prefix

        self.tables = {}
        self.names_types_map = {}
        self.root_table = None
        self.types_transforms = {}
        self.fields_transforms = {}
        self.ordered_tables_keys = []
        self.source_tree = ""
        self.target_tree = ""
        self.metadata = MetaData()
        self.processed_at = datetime.now()

        self._build_model()

    @property
    def fk_ordered_tables(
        self,
    ) -> Iterable[Union[DataModelTableDuplicated, DataModelTableReused]]:
        """Yields tables in create/insert order (tables referenced in foreign keys first)"""
        for key in self.ordered_tables_keys:
            yield self.tables[key]

    @property
    def fk_ordered_tables_reversed(
        self,
    ) -> Iterable[Union[DataModelTableDuplicated, DataModelTableReused]]:
        """Yields tables in drop/delete order (tables referencing foreign keys first)"""
        for key in reversed(self.ordered_tables_keys):
            yield self.tables[key]

    def _create_table_model(
        self,
        table_name: str,
        type_name: str,
        is_root_table: bool = False,
        is_virtual_node: bool = False,
    ) -> Union[DataModelTableReused, DataModelTableDuplicated]:
        """Helper to create a data table model

        :param table_name: name of the table
        :param type_name: type of the table
        :param is_root_table: is this table the root table?
        :param is_virtual_node: was this table created to store multiple root elements?
        :return: a data table model
        """
        table_config = self.model_config.get("tables", {}).get(table_name, {})
        if table_config.get("reuse", True):
            return DataModelTableReused(
                table_name,
                type_name,
                is_root_table,
                is_virtual_node,
                self.metadata,
                table_config,
                self.db_schema,
                self.temp_prefix,
                self,
            )
        else:
            return DataModelTableDuplicated(
                table_name,
                type_name,
                is_root_table,
                is_virtual_node,
                self.metadata,
                table_config,
                self.db_schema,
                self.temp_prefix,
                self,
            )

    def _build_model(self):
        """Build model from the provided XSD schema and config.

        It will parse the XML schema, then simplify it, then create all sqlalchemy objects.
        """
        # parse the XML schema recursively and hold a reference to the head table
        root_table = self._parse_tree(
            self.xml_schema[0] if len(self.xml_schema) == 1 else self.xml_schema,
            is_root_table=True,
        )
        self.root_table = root_table.type_name
        # compute a text representation of the original data model and store it
        self.source_tree = "\n".join(self._repr_tree(root_table))
        # check user-provided configuration for tables
        for tb_config in self.model_config.get("tables", {}):
            if tb_config not in self.names_types_map:
                raise DataModelConfigError(
                    f"Table '{tb_config}' provided in config does not exist"
                )
        # simplify the data model recursively starting from the root table
        self.types_transforms, self.fields_transforms = root_table.simplify_table()
        # remove tables that have been flagged for deletion during the simplification process
        root_table.keep_table = True
        self.tables = {
            key: tb for key, tb in self.tables.items() if hasattr(tb, "keep_table")
        }
        # compute a text representation of the simplified data model and store it
        self.target_tree = "\n".join(self._repr_tree(root_table))
        # add parent table information on each table when it is not reused
        # raises an error if a table is not configured as "reused" and have more than 1 parent table
        for tb in self.tables.values():
            tb.compute_dependencies()
        # build a list of tables in insert/create order
        ts = TopologicalSorter(
            {key: sorted(tb.dependencies) for key, tb in self.tables.items()}
        )
        self.ordered_tables_keys = list(ts.static_order())
        # build the ordered table in the sqlalchemy Metadata object (cannot be done before simplification because
        # it will fail if we attempt to recreate tables that already exist in the sqlalchemy metadata
        for tb in self.fk_ordered_tables:
            tb.build_sqlalchemy_tables()

    def _parse_tree(
        self, parent_node: xmlschema.XsdElement, is_root_table: bool = False
    ):
        """Parse a node of an XML schema recursively and create a target data model without any simplification

        We parse the XSD tree recursively to create for each node (basically a complex type in the XSD) an equivalent \
        DataModelTable (which represents a table in the target data model). By default, tables are named after the \
        first field name of this type. This is because we hope that fields names will be 'better' than actual \
        type names. To be on the safe side, we need to make our new table names unique in the event where different \
        XSD types are used with the same field names somewhere in the data model. Actual XSD types names and our \
        table names are bijective.
        This step is fairly straightforward, as we create DataModelTable objects recursively along the XSD tree, and \
        populate them with appropriate columns and relations.

        :param parent_node: the current XSD node being parsed
        :param is_root_table: True if this is the root table
        """

        # find current node type and name and returns corresponding table if it already exists
        parent_type = (
            parent_node.type.local_name
            if hasattr(parent_node, "type")
            else self.data_flow_name
        )
        if parent_type is None:
            parent_type = parent_node.local_name

        # if this type has already been encountered, stop here and return existing table
        if parent_type in self.tables:
            parent_table = self.tables[parent_type]
            return parent_table

        # elements names and types should be bijective. If an element name is used for different types,
        # we add a suffix to the name to make it unique again (using a dict to keep the name/type association)
        parent_name = (
            parent_node.local_name
            if hasattr(parent_node, "local_name")
            else self.data_flow_name
        )
        if parent_name in self.names_types_map:
            i = 1
            while "_".join([parent_name, str(i)]) in self.names_types_map:
                i += 1
            parent_name = "_".join([parent_name, str(i)])
        self.names_types_map[parent_name] = parent_type

        # create a new table object associated with the element
        parent_table = self._create_table_model(
            parent_name,
            parent_type,
            is_root_table,
            isinstance(parent_node, xmlschema.XMLSchema),
        )
        self.tables[parent_type] = parent_table

        def recurse_parse_simple_type(elem_type):
            """Parse simple types to extract properties in case of restrictions, unions, and nested forms"""
            if len(elem_type) > 1:
                data_types = []
                min_lengths = []
                max_lengths = []
                allow_empties = []
                for el_type in elem_type:
                    dt, mil, mal, ae = recurse_parse_simple_type([el_type])
                    data_types.append(dt)
                    min_lengths.append(mil)
                    max_lengths.append(mal)
                    allow_empties.append(ae)
                return (
                    data_types[0] if len(set(data_types)) == 1 else "string",
                    (
                        min(min_lengths)
                        if all(e is not None for e in min_lengths)
                        else None
                    ),
                    (
                        max(max_lengths)
                        if all(e is not None for e in max_lengths)
                        else None
                    ),
                    any(allow_empties),
                )
            elem_type = elem_type[0]
            if elem_type.is_union():
                return (
                    recurse_parse_simple_type(elem_type.base_type.member_types)
                    if elem_type.base_type
                    else recurse_parse_simple_type(elem_type.member_types)
                )
            if elem_type.is_restriction():
                dt = elem_type.base_type.local_name
                mil = elem_type.min_length
                mal = elem_type.max_length
                ae = elem_type.allow_empty
                if elem_type.base_type.is_restriction():
                    bt_dt, bt_mil, bt_mal, bt_ae = recurse_parse_simple_type(
                        [elem_type.base_type]
                    )
                    dt = bt_dt
                    mil = (
                        min(mil, bt_mil)
                        if mil is not None and bt_mil is not None
                        else None
                    )
                    mal = (
                        max(mal, bt_mal)
                        if mal is not None and bt_mal is not None
                        else None
                    )
                    ae = ae and bt_ae if ae is not None and bt_ae is not None else None
                if elem_type.enumeration is not None:
                    mil = min([len(val) for val in elem_type.enumeration])
                    mal = max([len(val) for val in elem_type.enumeration])
                return dt, mil, mal, ae
            return (
                elem_type.local_name,
                elem_type.min_length,
                elem_type.max_length,
                elem_type.allow_empty,
            )

        def get_occurs(particle):
            parent_occurs = [1, 1]
            if particle.parent and hasattr(particle.parent, "model"):
                parent_occurs = get_occurs(particle.parent)
                if particle.parent.model == "choice":
                    parent_occurs[0] = 0
            return [
                min(parent_occurs[0], particle.min_occurs),
                (
                    max(parent_occurs[1], particle.max_occurs)
                    if parent_occurs[1] is not None and particle.max_occurs is not None
                    else None
                ),
            ]

        # go through item attributes and add them as columns
        for attrib_name, attrib in parent_node.attributes.items():
            (
                data_type,
                min_length,
                max_length,
                allow_empty,
            ) = recurse_parse_simple_type([attrib.type])
            parent_table.add_column(
                f"{attrib_name}",
                data_type,
                [0, 1],
                min_length,
                max_length,
                True,
                False,
                allow_empty,
                None,
            )
        nested_containers = []
        # go through the children to add either arguments either relations to the current element
        for child in parent_node:
            if type(child) is xmlschema.XsdElement:
                # "nested_containers" is used to allow ordering nodes in mostly correct order in case of nested sequence
                # with multiple occurrence when generating XML. For instance, if we have a sequence A, B with
                # max occur > 1, we want to generate A, B, A, B and not A, A, B, B, thus we mark A and B as member of
                # the same "ngroup", which will be used when generating XML
                if (
                    len(nested_containers) > 1
                    and child.parent == nested_containers[-2][0]
                ):
                    nested_containers.pop()
                elif (
                    len(nested_containers) == 0
                    or child.parent != nested_containers[-1][0]
                ):
                    nested_containers.append(
                        (
                            child.parent,
                            (
                                str(hash(child.parent))
                                if child.parent
                                and child.parent.max_occurs != 1
                                and child.parent.model != "choice"
                                else None
                            ),
                        )
                    )
                ct = child.type
                if (
                    ct.is_complex()
                    and len(child) == 0
                    and len(child.attributes) == 0
                    and ct.base_type is not None
                ):
                    ct = ct.base_type
                if ct.is_simple():
                    (
                        data_type,
                        min_length,
                        max_length,
                        allow_empty,
                    ) = recurse_parse_simple_type([ct])
                    occurs = get_occurs(child)
                    parent_table.add_column(
                        child.local_name,
                        data_type,
                        occurs,
                        min_length,
                        max_length,
                        False,
                        False,
                        allow_empty,
                        nested_containers[-1][1],
                    )

                elif ct.is_complex():
                    child_table = self._parse_tree(child)
                    child_table.model_group = (
                        "choice"
                        if ct.model_group and ct.model_group.model == "choice"
                        else "sequence"
                    )
                    occurs = get_occurs(child)
                    if child.is_single():
                        parent_table.add_relation_1(
                            child.local_name,
                            child_table,
                            occurs,
                            nested_containers[-1][1],
                        )
                    else:
                        parent_table.add_relation_n(
                            child.local_name,
                            child_table,
                            occurs,
                            nested_containers[-1][1],
                        )
                else:
                    raise ValueError("unknown case; please check")
            else:
                raise ValueError("unknown case; please check (child not an XsdElement)")

        if hasattr(parent_node, "type") and (
            parent_node.type.has_mixed_content()
            or parent_node.type.has_simple_content()
        ):
            if parent_node.type.base_type is not None:
                (
                    data_type,
                    min_length,
                    max_length,
                    allow_empty,
                ) = recurse_parse_simple_type([parent_node.type.base_type])
            else:
                data_type, min_length, max_length, allow_empty = "string", 0, None, True

            parent_table.add_column(
                "value",
                data_type,
                [0, 1],
                min_length,
                max_length,
                False,
                True,
                allow_empty,
                None,
            )

        return parent_table

    def _repr_tree(
        self,
        parent_table: Union[DataModelTableReused, DataModelTableDuplicated],
        visited_nodes=None,
    ):
        """Build a text representation of the data model tree

        :param parent_table: the current data model table object
        """
        if visited_nodes is None:
            visited_nodes = set()
        else:
            visited_nodes = {item for item in visited_nodes}
        visited_nodes.add(parent_table.name)
        for field_type, name, field in parent_table.fields:
            if field_type == "col":
                yield f"{field.name}{field.occurs}: {field.data_type}"
            elif field_type == "rel1":
                mg = " (choice)" if field.other_table.model_group == "choice" else ""
                yield f"{field.name}{field.occurs}{mg}:{' ...' if field_type in visited_nodes else ''}"
                if field.other_table.name not in visited_nodes:
                    for line in self._repr_tree(field.other_table, visited_nodes):
                        yield f"    {line}"
            elif field_type == "reln":
                mg = " (choice)" if field.other_table.model_group == "choice" else ""
                yield f"{field.name}{field.occurs}{mg}:{' ...' if field_type in visited_nodes else ''}"
                for line in self._repr_tree(field.other_table, visited_nodes):
                    yield f"    {line}"

    def get_entity_rel_diagram(self, text_context=True) -> str:
        """Build an entity relationship diagram for the data model

        The ERD syntax is used by mermaid.js to create a visual representation of the diagram, which is supported
        by Pycharm IDE or GitHub in markdown files, among others

        :param text_context: Should we add a title, a text explanation, etc. or just the ERD?
        :return: A string representation of the ERD
        """
        out = ["erDiagram"]
        for tb in self.fk_ordered_tables_reversed:
            out += tb.get_entity_rel_diagram()

        if text_context:
            out = (
                [
                    f"# {self.data_flow_long_name}\n",
                    f"### Data model name: `{self.data_flow_name}`\n",
                    (
                        "The following *Entity Relationships Diagram* represents the target data model, after the "
                        "simplification of the source data model, but before the transformations performed to optimize "
                        "data storage (transformation of `1-1` and `1-n` relationships into `n-1` and `n-n` "
                        "relationships, respectively, as described [here](../../docs/recycling_nodes.md)).\n"
                    ),
                    (
                        "As a consequence, not all tables of the actual data model used in the database are shown. "
                        "Specifically, `1-n` relationships presented may be stored in the database using an additional "
                        "relationship table (noted with an asterisk in the relationship name).\n"
                    ),
                    "```mermaid",
                ]
                + out
                + [
                    "```",
                    (
                        "`-N` suffix in field type indicates that the field can have multiple values, which will be "
                        "stored as comma separated values."
                    ),
                ]
            )
        return "\n".join(out)

    def get_all_create_table_statements(self, temp=False) -> Iterable[CreateTable]:
        """Yield create table statements for all tables

        :param temp: If True, yield create table statements for temporary tables (prefixed)
        """
        for tb in self.fk_ordered_tables:
            yield from tb.get_create_table_statements(temp)

    def get_all_create_index_statements(self) -> Iterable[CreateIndex]:
        """Yield create index statements for all tables"""
        for tb in self.fk_ordered_tables:
            yield from tb.get_create_index_statements()

    def create_all_tables(self, temp: bool = False) -> None:
        """Create tables for the data model, either target tables or temp tables used to import data

        :param temp: If True, create temporary (prefixed) tables
        """
        for tb in self.fk_ordered_tables:
            tb.create_tables(self.engine, temp)

    def create_db_schema(self) -> None:
        """Create database schema if it does not already exist."""
        if self.db_schema is not None:
            inspector = inspect(self.engine)
            if self.db_schema not in inspector.get_schema_names():
                with self.engine.connect() as conn:
                    conn.execute(sqlalchemy.schema.CreateSchema(self.db_schema))
                    conn.commit()
                logger.info(f"Created schema: {self.db_schema}")

    def drop_all_tables(self):
        """Drop the data model target (unprefixed) tables.

        BE CAUTIOUS, THIS METHOD DROPS TABLES WITHOUT FURTHER NOTICE!

        """
        for tb in self.fk_ordered_tables_reversed:
            tb.drop_tables(self.engine)

    def drop_all_temp_tables(self):
        """Drop the data model temporary (prefixed) tables.

        BE CAUTIOUS, THIS METHOD DROPS TABLES WITHOUT FURTHER NOTICE!

        """
        for tb in self.fk_ordered_tables_reversed:
            tb.drop_temp_tables(self.engine)

    def parse_xml(
        self,
        xml_file: Union[str, BytesIO],
        xml_file_path: str = None,
        skip_validation: bool = True,
    ) -> document.Document:
        """Parse an XML document based on this data model

        This method is just a wrapper around the parse_xml method of the Document class.

        :param xml_file: The path or the file object of an XML file to parse
        :param xml_file_path: The path of the XML file, mandatory if xml_file is file object in order to fill the \
        'xml2db_input_file_path' column of the root table.
        :param skip_validation: Should we validate the documents against the schema first?
        :return: A parsed `Document` object
        """
        doc = document.Document(self)
        doc.parse_xml(xml_file, xml_file_path, skip_validation)
        return doc

    def extract_from_database(
        self,
        root_select_where: str,
        force_tz: Union[str, None] = None,
    ) -> document.Document:
        """Extract a document from the database, based on a where clause applied to the root table. For instance, you
        can use the column `xml2db_input_file_path` to filter the data loaded from a specific file.

        :param root_select_where: A where clause to apply to this root table, as a string
        :param force_tz: Apply this timezone if database returns timezone-naïve datetime
        :return: A `Document` object containing extracted data
        """
        doc = document.Document(self)
        doc.extract_from_database(self.root_table, root_select_where, force_tz=force_tz)
        return doc
