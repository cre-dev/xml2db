import csv
import datetime
import logging
import multiprocessing
from hashlib import sha1
from io import BytesIO
from typing import Union, TYPE_CHECKING, Dict
from zoneinfo import ZoneInfo
from sqlalchemy import Column, Table, text, select
from sqlalchemy.engine import Connection
from sqlalchemy.sql.expression import TextClause
from lxml import etree

if TYPE_CHECKING:
    from .model import DataModel

from xml2db.exceptions import DataModelConfigError
from xml2db.xml_converter import XMLConverter

logger = logging.getLogger(__name__)


class Document:
    """A class to represent a single XML file with its data, based on a given XSD.

    Based on a given DataModel object which represents the data model defined in the XSD, this class deals with \
    the data itself. It allows parsing an XML file to extract the data into the data model format \
     (performing the transforms defined in the DataModel object) and inserting the data into the database.

    :param model: A `DataModel` object for this document
    """

    def __init__(self, model: "DataModel"):
        self.model = model
        self.data = {}
        self.xml_file_path = None

    def parse_xml(
        self,
        xml_file: Union[str, BytesIO],
        xml_file_path: str = None,
        skip_validation: bool = True,
    ) -> None:
        """Parse an XML document and apply transformation corresponding to the target data model

        This method will first parse the XML file into a dict (document tree) using lxml
        and then compute hash for all nodes based on their content, and finally convert
        the document tree to tables data, creating primary keys and relations, ready to
        be inserted in the database.

        :param xml_file: the path or the file object of an XML file to parse
        :param xml_file_path: path of the XML file, must be provided if 'xml_file' is provided as a file object \
        (type 'BytesIO'), in order to fill the 'xml2db_input_file_path' column of the root table.
        :param skip_validation: should we validate the document against the schema first? default to skip for \
        backward compatibility
        """
        if type(xml_file) == BytesIO:
            if xml_file_path is None:
                error_message = (
                    "If 'xml_file' is provided as a file object (type 'BytesIO') then 'xml_file_path' must be provided "
                    "too in order to fill the 'xml2db_input_file_path' column of the root table."
                )
                logger.error(error_message)
                raise ValueError(error_message)
        self.xml_file_path = xml_file_path if xml_file_path is not None else xml_file

        document_tree = self.model.xml_converter.parse_xml(
            xml_file, self.xml_file_path, skip_validation
        )

        logger.info(f"Computing records hashes for {self.xml_file_path}")
        self._compute_records_hashes(document_tree)

        if "document_tree_hook" in self.model.model_config:
            if not callable(self.model.model_config["document_tree_hook"]):
                raise DataModelConfigError(
                    "document_tree_hook provided in config must be callable"
                )
            logger.info(f"Running document_tree_hook function for {self.xml_file_path}")
            document_tree = self.model.model_config["document_tree_hook"](document_tree)

        logger.info(f"Adding records to data model for {self.xml_file_path}")
        self.data = self.doc_tree_to_flat_data(document_tree)

        logger.debug(self.__repr__())

    def to_xml(
        self, out_file: str = None, nsmap: dict = None, indent: str = "  "
    ) -> etree.Element:
        """Convert a document tree (nested dict) into an XML file

        :param out_file: If provided, write output to a file.
        :param nsmap: An optional namespace mapping.
        :param indent: A string used as indentin XML output.
        :return: The etree object corresponding to the root XML node.
        """
        converter = XMLConverter(self.model)
        converter.document_tree = self.flat_data_to_doc_tree()
        return converter.to_xml(out_file=out_file, nsmap=nsmap, indent=indent)

    def _compute_records_hashes(self, node: Dict) -> bytes:
        """Compute the hash of records recursively, taking into account children, for deduplication purpose.

        :param node: a node of the parsed document tree
        :return: the hash string representation of the node
        """
        if node is None:
            return b""
        h = sha1()
        table = self.model.tables[node["type"]]
        for field_type, name, _ in table.fields:
            if field_type == "col":
                h.update(str(node["content"].get(name, None)).encode("utf-8"))
            elif field_type == "rel1":
                h.update(
                    self._compute_records_hashes(node["content"].get(name, [None])[0])
                )
            elif field_type == "reln":
                h_children = [
                    self._compute_records_hashes(v)
                    for v in node["content"].get(name, [])
                ]
                for h_child in sorted(h_children):
                    h.update(h_child)
        node["record_hash"] = h.digest()
        return node["record_hash"]

    def doc_tree_to_flat_data(self, document_tree: dict) -> dict:
        """Convert document tree (nested dict) to flat tables data model to prepare database import

        :param document_tree: A nested dict which represents an XML document
        :returns: A dict containing flat tables
        """

        def _extract_node(
            node: Dict, pk_parent_node: int, row_number: int, data_model: dict
        ) -> int:
            """Extract nodes recursively

            :param node: a dict containing a node of the document tree
            :param pk_parent_node: the primary key of its parent node
            :param data_model: the dict to write output to
            :return: the primary key given to this node
            """

            # get the corresponding table model
            model_table = self.model.tables[node["type"]]

            # initialize data structure
            if node["type"] not in data_model:
                data_model[node["type"]] = {"next_pk": 1, "records": []}
                if model_table.is_reused:
                    data_model[node["type"]]["hashmap"] = {}
                if any(
                    [
                        rel.other_table.is_reused
                        for rel in model_table.relations_n.values()
                    ]
                ):
                    data_model[node["type"]]["relations_n"] = {
                        rel.rel_table_name: {"next_pk": 1, "records": []}
                        for rel in model_table.relations_n.values()
                        if rel.other_table.is_reused
                    }
            data = data_model[node["type"]]

            hex_hash = str(node["record_hash"])

            # if node is reused and a record with identical hash is already inserted, return its pk
            if model_table.is_reused:
                if hex_hash in data["hashmap"]:
                    return data["hashmap"][hex_hash]

            record = {}

            # add pk
            record_pk = data["next_pk"]
            record[f"temp_pk_{model_table.name}"] = record_pk
            data["next_pk"] += 1

            # add parent pk if node is not reused
            if not model_table.is_reused:
                record[f"temp_fk_parent_{model_table.parent.name}"] = pk_parent_node
                if self.model.model_config["row_numbers"]:
                    record["xml2db_row_number"] = row_number

            # build record from fields for columns and n-1 relations
            for field_type, key, _ in model_table.fields:
                if field_type == "col":
                    if key in node["content"]:
                        if model_table.columns[key].data_type in ["decimal", "float"]:
                            val = [float(v) for v in node["content"][key]]
                        elif model_table.columns[key].data_type == "integer":
                            val = [int(v) for v in node["content"][key]]
                        elif model_table.columns[key].data_type == "boolean":
                            val = [
                                v == "true" or v == "1" for v in node["content"][key]
                            ]
                        else:
                            val = node["content"][key]

                        if len(val) == 1:
                            record[key] = val[0]
                        else:
                            esc_val = [str(v).replace('"', '\\"') for v in val]
                            esc_val = [
                                (
                                    f'"{v}"'
                                    if "," in v or "\n" in v or "\r" in v or '"' in v
                                    else v
                                )
                                for v in esc_val
                            ]
                            record[key] = ",".join(esc_val)
                    else:
                        record[key] = None

                elif field_type == "rel1":
                    rel = model_table.relations_1[key]
                    if key in node["content"]:
                        record[f"temp_{rel.field_name}"] = _extract_node(
                            node["content"][key][0],
                            record_pk,
                            0,
                            data_model,
                        )
                    else:
                        record[f"temp_{rel.field_name}"] = None

            record["record_hash"] = bytes(node["record_hash"])

            # add integration meta data if root table
            if model_table.type_name == self.model.root_table:
                record["xml2db_input_file_path"] = self.xml_file_path
                record["xml2db_processed_at"] = self.model.processed_at

            # add n-n relationship data for reused children nodes
            for rel in model_table.relations_n.values():
                if rel.name in node["content"]:
                    if rel.other_table.is_reused:
                        rel_data = data["relations_n"][rel.rel_table_name]
                        i = 1
                        for rel_child in node["content"][rel.name]:
                            rel_row = {
                                f"temp_fk_{model_table.name}": record_pk,
                                f"temp_fk_{rel.other_table.name}": _extract_node(
                                    rel_child,
                                    record_pk,
                                    i,
                                    data_model,
                                ),
                            }
                            if self.model.model_config["row_numbers"]:
                                rel_row["xml2db_row_number"] = i
                            rel_data["records"].append(rel_row)
                            i += 1
                    else:
                        i = 1
                        for rel_child in node["content"][rel.name]:
                            _extract_node(rel_child, record_pk, i, data_model)
                            i += 1

            data["records"].append(record)

            if model_table.is_reused:
                data["hashmap"][hex_hash] = record_pk

            return record_pk

        flat_tables = {}
        _extract_node(document_tree, 0, 0, flat_tables)

        return flat_tables

    def flat_data_to_doc_tree(self) -> dict:
        """Convert the data stored in flat tables into a document tree (nested dict)

        :return: The document tree (nested dict)
        """
        data_index = {}

        # convert data to keyed dict for easier access
        temp = (
            ""
            if f"pk_{self.model.tables[self.model.root_table].name}"
            in self.data[self.model.root_table]["records"][0]
            else "temp_"
        )
        for tb in self.model.tables.values():
            data_index[tb.type_name] = {
                "records": {},
                "relations_n": {},
            }
            if tb.type_name in self.data:
                data_index[tb.type_name]["records"] = {
                    row[f"{temp}pk_{tb.name}"]: row
                    for row in self.data[tb.type_name]["records"]
                }
            for rel in tb.relations_n.values():
                index = {}
                if rel.other_table.is_reused:
                    if tb.type_name in self.data:
                        for row in self.data[tb.type_name]["relations_n"][
                            rel.rel_table_name
                        ]["records"]:
                            if row[f"{temp}fk_{tb.name}"] not in index:
                                index[row[f"{temp}fk_{tb.name}"]] = []
                            index[row[f"{temp}fk_{tb.name}"]].append(
                                row[f"{temp}fk_{rel.other_table.name}"]
                            )
                else:
                    if rel.other_table.type_name in self.data:
                        for row in self.data[rel.other_table.type_name]["records"]:
                            if row[f"{temp}fk_parent_{tb.name}"] not in index:
                                index[row[f"{temp}fk_parent_{tb.name}"]] = []
                            index[row[f"{temp}fk_parent_{tb.name}"]].append(
                                row[f"{temp}pk_{rel.other_table.name}"]
                            )
                data_index[tb.type_name]["relations_n"][rel.rel_table_name] = index

        def _build_node(node_type: str, node_pk: int) -> dict:
            """Build a dict node recursively

            :param node_type: The node type
            :param node_pk: The node primary key
            :return: A node as a dict
            """
            tb = self.model.tables[node_type]
            node = {
                "type": node_type,
                "content": {},
            }
            record = data_index[node_type]["records"][node_pk]
            for field_type, rel_name, rel in tb.fields:
                if field_type == "col" and record[rel_name] is not None:
                    if rel.data_type in [
                        "decimal",
                        "float",
                    ]:  # remove trailing ".0" for decimal and float
                        node["content"][rel_name] = [
                            value.rstrip("0").rstrip(".") if "." in value else value
                            for value in str(record[rel_name]).split(",")
                        ]
                    elif isinstance(record[rel_name], datetime.datetime):
                        node["content"][rel_name] = [
                            record[rel_name].isoformat(timespec="milliseconds")
                        ]
                    else:
                        node["content"][rel_name] = (
                            list(csv.reader([str(record[rel_name])], escapechar="\\"))[
                                0
                            ]
                            if "," in str(record[rel_name])
                            else [str(record[rel_name])]
                        )
                elif (
                    field_type == "rel1"
                    and record[f"{temp}{rel.field_name}"] is not None
                ):
                    node["content"][rel_name] = [
                        _build_node(
                            rel.other_table.type_name, record[f"{temp}{rel.field_name}"]
                        )
                    ]
                elif (
                    field_type == "reln"
                    and node_pk
                    in data_index[tb.type_name]["relations_n"][rel.rel_table_name]
                ):
                    node["content"][rel_name] = [
                        _build_node(rel.other_table.type_name, pk)
                        for pk in data_index[tb.type_name]["relations_n"][
                            rel.rel_table_name
                        ][node_pk]
                    ]
            return node

        return _build_node(
            self.model.root_table,
            int(list(data_index[self.model.root_table]["records"].keys())[0]),
        )

    def insert_into_temp_tables(self) -> None:
        """Insert data into temporary tables

        (Re)creates temp tables before inserting data.
        """
        logger.info(f"Dropping temp tables if exist for {self.xml_file_path}")
        self.model.drop_all_temp_tables()

        logger.info(f"Creating temp tables for {self.xml_file_path}")
        self.model.create_all_tables(temp=True)

        logger.info(f"Inserting data into temporary tables from {self.xml_file_path}")
        for tb in self.model.fk_ordered_tables:
            for query, data in tb.get_insert_temp_records_statements(
                self.data.get(tb.type_name, None)
            ):
                with self.model.engine.begin() as conn:
                    conn.execute(query, data)

    def merge_into_target_tables(self) -> int:
        """Merge data into target data model

        Execute all update and insert statements needed to merge temporary tables content \
        into target tables, within a transaction.

        :return: The number of inserted rows
        """
        inserted_rows_count = 0
        with self.model.engine.begin() as conn:
            for tb in self.model.fk_ordered_tables:
                for query in tb.get_merge_temp_records_statements():
                    result = conn.execute(query)
                    if query.is_insert:
                        inserted_rows_count += result.rowcount
        if inserted_rows_count == 0:
            logger.warning("No rows were inserted!")
        else:
            logger.info(f"Inserted rows: {inserted_rows_count}")

        return inserted_rows_count

    def insert_into_target_tables(
        self,
        db_semaphore: multiprocessing.Semaphore = None,
    ) -> int:
        """Insert and merge data into the database

        Insert data into temporary tables and then merge temporary tables into target tables.

        :param db_semaphore: An optional semaphore to avoid concurrent access to the database. When provided, it will \
            ensure that only one merging operation at a time is performed.
        :return: The number of inserted rows
        """
        try:
            self.model.create_db_schema()
            self.insert_into_temp_tables()
        except Exception as e:
            logger.error(
                f"Error while importing into temporary tables from {self.xml_file_path}"
            )
            logger.error(e)
            raise
        else:
            logger.info(
                f"Merging temporary tables into target tables for {self.xml_file_path}"
            )
            if db_semaphore is not None:
                db_semaphore.acquire()
            try:
                self.model.create_all_tables()  # Create target tables if not exist
                inserted_rows = self.merge_into_target_tables()
            except Exception as e:
                logger.error(
                    f"Error while merging temporary tables into target tables for {self.xml_file_path}"
                )
                logger.error(e)
                raise
            finally:
                if db_semaphore is not None:
                    db_semaphore.release()
        finally:
            logger.info(f"Dropping temporary tables for {self.xml_file_path}")
            self.model.drop_all_temp_tables()

        return inserted_rows

    def extract_from_database(
        self,
        root_table_name: str,
        root_select_where: str,
        force_tz: Union[str, None] = None,
    ) -> dict:
        """Extract a subtree from the database and store it in a flat format

        :param root_table_name: The root table name to start from
        :param root_select_where: A where clause to apply to this root table
        :param force_tz: Apply this timezone if database returns timezone-naïve datetime
        :return: A shallow dict of flat data tables
        """

        if force_tz:
            force_tz = ZoneInfo(force_tz)

        def _fetch_data(
            sqla_table: Table,
            key_column: Column,
            join_sequence: list[tuple[Column, Table, Column]],
            top_where_clause: TextClause,
            order_by: Union[None, tuple[Column]],
            append_to: list,
            conn: Connection,
        ):
            """Fetch data from a specific table and write fetched rows in a dict keyed by the first row column"""
            quer = select(*(sqla_table.columns.values()))

            join_sequence = join_sequence.copy()
            if len(join_sequence) > 0:
                left_col, join_tb, right_col = join_sequence.pop()
                sub_quer = select(right_col)
                prev_join_col = left_col
                for left_col, join_tb, right_col in reversed(join_sequence):
                    sub_quer = sub_quer.join(join_tb, right_col == prev_join_col)
                    prev_join_col = left_col
                sub_quer = sub_quer.where(top_where_clause)
                quer = quer.where(key_column.in_(sub_quer))
            else:
                quer = quer.where(top_where_clause)

            if order_by:
                quer = quer.order_by(*order_by)

            def add_tz(x):
                if (
                    force_tz
                    and isinstance(x, datetime.datetime)
                    and (x.tzinfo is None or x.tzinfo.utcoffset(x) is None)
                ):
                    x = x.replace(tzinfo=force_tz)
                return x

            col_names = sqla_table.columns.keys()
            for row in conn.execute(quer):
                append_to.append({key: add_tz(val) for key, val in zip(col_names, row)})

        def _do_extract_table(
            tb,
            top_where_clause,
            parent_table,
            join_sequence,
            res_dict,
            conn,
        ):
            """Fetch tables and relationship tables recursively"""
            if tb.type_name not in res_dict:
                res_dict[tb.type_name] = {"records": []}
            _fetch_data(
                tb.table,
                (
                    getattr(tb.table.c, f"pk_{tb.name}")
                    if tb.is_reused
                    else getattr(tb.table.c, f"fk_parent_{parent_table.name}")
                ),
                join_sequence,
                top_where_clause,
                (
                    None
                    if tb.is_reused or not tb.data_model.model_config["row_numbers"]
                    else (
                        getattr(tb.table.c, f"fk_parent_{parent_table.name}"),
                        tb.table.c.xml2db_row_number,
                    )
                ),
                res_dict[tb.type_name]["records"],
                conn,
            )
            join_root = (
                [(None, tb.table, getattr(tb.table.c, f"pk_{tb.name}"))]
                if parent_table is None
                else []
            )
            if len(tb.relations_n) > 0:
                if "relations_n" not in res_dict[tb.type_name]:
                    res_dict[tb.type_name]["relations_n"] = {}
                for rel in tb.relations_n.values():
                    if rel.rel_table_name not in res_dict[tb.type_name]["relations_n"]:
                        res_dict[tb.type_name]["relations_n"][rel.rel_table_name] = {
                            "records": []
                        }
                    new_join = []
                    if not tb.is_reused:
                        new_join = [
                            (
                                getattr(tb.table.c, f"fk_parent_{parent_table.name}"),
                                tb.table,
                                getattr(tb.table.c, f"pk_{tb.table.name}"),
                            )
                        ]
                    if rel.other_table.is_reused:
                        _fetch_data(
                            rel.rel_table,
                            getattr(rel.rel_table.c, f"fk_{tb.name}"),
                            join_sequence + join_root + new_join,
                            top_where_clause,
                            (
                                (
                                    getattr(rel.rel_table.c, f"fk_{tb.name}"),
                                    rel.rel_table.c.xml2db_row_number,
                                )
                                if tb.data_model.model_config["row_numbers"]
                                else None
                            ),
                            res_dict[tb.type_name]["relations_n"][rel.rel_table_name][
                                "records"
                            ],
                            conn,
                        )
                        new_join = new_join + [
                            (
                                getattr(rel.rel_table.c, f"fk_{tb.name}"),
                                rel.rel_table,
                                getattr(rel.rel_table.c, f"fk_{rel.other_table.name}"),
                            )
                        ]
                    _do_extract_table(
                        rel.other_table,
                        top_where_clause,
                        tb,
                        join_sequence + join_root + new_join,
                        res_dict,
                        conn,
                    )
            for rel in tb.relations_1.values():
                _do_extract_table(
                    rel.other_table,
                    top_where_clause,
                    tb,
                    join_sequence
                    + [
                        (
                            getattr(
                                tb.table.c,
                                (
                                    f"pk_{tb.name}"
                                    if tb.is_reused
                                    else f"fk_parent_{parent_table.name}"
                                ),
                            ),
                            tb.table,
                            getattr(tb.table.c, f"{rel.field_name}"),
                        )
                    ],
                    res_dict,
                    conn,
                )

        flat_tables = {}

        with self.model.engine.connect() as conn:
            _do_extract_table(
                self.model.tables[root_table_name],
                text(root_select_where),
                None,
                [],
                flat_tables,
                conn,
            )

        self.data = flat_tables
        return flat_tables

    def __repr__(self) -> str:
        """Output a repr string for the current document with records count"""
        settings = (
            f"temp_prefix: {self.model.temp_prefix}, db_schema: {self.model.db_schema}"
        )
        if not self.data:
            return f"Empty {self.model.data_flow_name} document ({settings})"
        else:
            n = sum([len(v["records"]) for v in self.data.values()])
            return "\n".join(
                [
                    f"Parsed {self.xml_file_path} into a {self.model.data_flow_name} document: {n} records",
                    f"({settings})",
                ]
                + [
                    f"   {self.model.tables[k].name}: {len(v['records'])}"
                    for k, v in self.data.items()
                ]
            )
