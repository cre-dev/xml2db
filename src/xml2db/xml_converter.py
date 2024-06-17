import typing
from datetime import datetime
from typing import Union, Tuple
import logging
from lxml import etree
from io import BytesIO
from itertools import zip_longest
from hashlib import sha1

from .exceptions import DataModelConfigError


if typing.TYPE_CHECKING:
    from .model import DataModel

logger = logging.getLogger(__name__)


def remove_record_hash(node) -> None:
    """Remove hash data recursively from document tree. Only used for tests, in order to compare document trees with
    data extracted from the database (which does not always store record hash).

    Args:
        node: a node from the document tree
    """
    if "record_hash" in node:
        del node["record_hash"]
    if "content" in node:
        for _, val in node["content"].items():
            for child in val:
                if isinstance(child, dict):
                    remove_record_hash(child)


class XMLConverter:
    def __init__(self, data_model: "DataModel", document_tree: dict = None):
        """A class to convert data from document tree format (nested dict) to and from XML.

        Args:
            data_model: The [`DataModel`](./data_model.md#xml2db.model.DataModel) object used to parse XML files
            document_tree: Data in the document tree format (optional, can be built later by the `parse_xml` method)
        """
        self.model = data_model
        self.document_tree = document_tree

    def parse_xml(
        self,
        xml_file: Union[str, BytesIO],
        file_path: str = None,
        skip_validation: bool = False,
        recover: bool = False,
        iterparse: bool = True,
    ) -> dict:
        """Parse an XML document into a nested dict and performs the simplifications defined in the
        DataModel object ("pull" child to upper level, transform a choice model into "type" and "value"
        fields or concatenate children as string).

        Args:
            xml_file: An XML file path or file content to be converted
            file_path: The file path to be printed in logs
            skip_validation: Whether we should validate XML against the schema before parsing
            recover: Try to process malformed XML (lxml option)
            iterparse: Parse XML using iterative parsing, which is a bit slower but uses less memory

        Returns:
            The parsed data in the document tree format (nested dict)
        """

        xt = None
        if not iterparse:
            logger.info("Parsing XML file")
            xt = etree.parse(xml_file)

        if skip_validation:
            logger.info("Skipping XML file validation")
        else:
            logger.info("Validating XML file against the schema")
            if not self.model.xml_schema.is_valid(xt if xt else xml_file):
                logger.error(f"XML file {file_path} does not conform with the schema")
                raise ValueError(
                    f"XML file {file_path} does not conform with the schema"
                )
            logger.info("XML file conforms with the schema")

        if iterparse:
            self.document_tree = self._parse_iterative(xml_file, recover)
        else:
            self.document_tree = self._parse_element_tree(xt)

        return self.document_tree

    def _parse_element_tree(self, xt: etree.ElementTree) -> dict:
        """Parse an etree.ElementTree recursively

        Args:
            xt: an XML ElementTree object

        Returns:
            The parsed document tree (nested dict)
        """
        if self.model.tables[self.model.root_table].is_virtual_node:
            doc = etree.Element(self.model.root_table)
            doc.append(xt.getroot())
        else:
            doc = xt.getroot()
        hash_maps = {}

        return self._parse_xml_node(self.model.root_table, doc, True, hash_maps)

    def _parse_xml_node(
        self, node_type: str, node: etree.Element, compute_hash: bool, hash_maps: dict
    ) -> dict:
        """Parse nodes of an XML document into a dict recursively

        Args:
            node_type: type of the node to parse
            node: lxml node object
            compute_hash: should we compute hash and deduplicate?
            hash_maps: a dict referencing nodes based on their hash

        Returns:
            a dict representing the node content
        """

        result = {"type": node_type, "content": {}}

        for key, val in node.attrib.items():
            if (
                key
                != "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation"
            ):
                result["content"][key] = [val]

        if node.text and node.text.strip():
            result["content"]["value"] = [node.text.strip()]

        for element in node.iterchildren():
            key = element.tag.split("}")[1] if "}" in element.tag else element.tag
            node_type_key = (node_type, key)
            value = None
            if element.text and element.text.strip():
                value = element.text
            transform = self.model.fields_transforms.get(node_type_key, (None, "join"))[
                1
            ]
            if transform != "join":
                value = self._parse_xml_node(
                    self.model.fields_transforms[node_type_key][0],
                    element,
                    transform not in ["elevate", "elevate_wo_prefix"],
                    hash_maps,
                )
            if key in result["content"]:
                result["content"][key].append(value)
            else:
                result["content"][key] = [value]

        self._transform_node(result)

        if compute_hash:
            return self._compute_hash_deduplicate(result, hash_maps)

        return result

    def _parse_iterative(
        self, xml_file: Union[str, BytesIO], recover: bool = False
    ) -> dict:
        """Parse an XML file into a document tree (nested dict) in an iterative fashion.

        This method uses etree.iterparse and does not load the entire XML document in memory.
        It saves memory, especially if you decide to filter out nodes using 'document_tree_node_hook' hook.

        Args:
            xml_file: an XML file to parse
            recover: should we try to parse incorrect XML?

        Returns:
            A document tree (nested dict)
        """
        nodes_stack = [
            {
                "type": (
                    self.model.root_table
                    if self.model.tables[self.model.root_table].is_virtual_node
                    else None
                ),
                "content": {},
            }
        ]
        hash_maps = {}

        joined_values = False
        for event, element in etree.iterparse(
            xml_file, recover=recover, events=["start", "end"]
        ):
            key = element.tag.split("}")[1] if "}" in element.tag else element.tag
            if event == "start":
                node_type, transform = self._get_node_type_transform(nodes_stack, key)
                joined_values = transform == "join"
                if not joined_values:
                    node = {"type": node_type, "content": {}}
                    for attrib_key, attrib_val in element.attrib.items():
                        if (
                            attrib_key
                            != "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation"
                        ):
                            node["content"][attrib_key] = [attrib_val]
                    nodes_stack.append(node)

            elif event == "end":
                # joined_values was set with the previous "start" event just before
                if joined_values:
                    if element.text and element.text.strip():
                        if key in nodes_stack[-1]["content"]:
                            nodes_stack[-1]["content"][key].append(element.text)
                        else:
                            nodes_stack[-1]["content"][key] = [element.text]
                else:
                    node = nodes_stack.pop()
                    node_type, transform = self._get_node_type_transform(
                        nodes_stack, key
                    )
                    if element.text and element.text.strip():
                        node["content"]["value"] = [element.text.strip()]
                    self._transform_node(node)
                    if transform not in ["elevate", "elevate_wo_prefix"]:
                        node = self._compute_hash_deduplicate(node, hash_maps)
                    if node:
                        if key in nodes_stack[-1]["content"]:
                            nodes_stack[-1]["content"][key].append(node)
                        else:
                            nodes_stack[-1]["content"][key] = [node]
                joined_values = False
                element.clear(keep_tail=True)

        # return the outer container only if root table is a "virtual" node, else return the XML root node
        if nodes_stack[0]["type"]:
            res = nodes_stack[0]
            self._transform_node(res)
            return self._compute_hash_deduplicate(res, hash_maps)
        for k, v in nodes_stack[0]["content"].items():
            return v[0]

    def _transform_node(self, node: dict):
        """Apply transformations to a given node, in place

        Args:
            node: the node to transform
        """
        for key in list(node["content"]):
            node_type_key = (node["type"], key)
            if node_type_key in self.model.fields_transforms:
                transform = self.model.fields_transforms[node_type_key][1]
                if transform == "elevate" or transform == "elevate_wo_prefix":
                    prefix = f"{key}_" if transform == "elevate" else ""
                    child = node["content"][key][0]
                    child_content = child["content"]
                    del node["content"][key]
                    for child_key, val in child_content.items():
                        node["content"][f"{prefix}{child_key}"] = val

        if node["type"] in self.model.types_transforms:
            if self.model.types_transforms[node["type"]] == "choice":
                node["content"] = [
                    {"type": [child_key], "value": val}
                    for child_key, val in node["content"].items()
                ][0]

    def _get_node_type_transform(self, nodes_stack, key) -> Tuple:
        if nodes_stack[-1]["type"]:
            node_type_key = (nodes_stack[-1]["type"], key)
            return self.model.fields_transforms.get(node_type_key, (None, "join"))
        return self.model.root_table, None

    def _compute_hash_deduplicate(self, node: dict, hash_maps: dict) -> dict:
        """
        A function to compute hash for a document tree node dict

        Args:
            node: a document tree node dict

        Returns:
            a node after deduplication
        """
        h = sha1()
        table = self.model.tables[node["type"]]
        for field_type, name, _ in table.fields:
            if field_type == "col":
                h.update(str(node["content"].get(name, None)).encode("utf-8"))
            elif field_type == "rel1":
                h.update(
                    node["content"][name][0]["record_hash"]
                    if name in node["content"]
                    else b""
                )
            elif field_type == "reln":
                h_children = [v["record_hash"] for v in node["content"].get(name, [])]
                for h_child in sorted(h_children):
                    h.update(h_child)
        node_hash = h.digest()
        node["record_hash"] = node_hash

        node_type = node["type"]
        if node_type not in hash_maps:
            hash_maps[node_type] = {}
        if node_hash in hash_maps[node_type]:
            node = hash_maps[node_type][node_hash]
        else:
            if "document_tree_node_hook" in self.model.model_config:
                if not callable(self.model.model_config["document_tree_node_hook"]):
                    raise DataModelConfigError(
                        "document_tree_node_hook provided in config must be callable"
                    )
                node = self.model.model_config["document_tree_node_hook"](node)
            hash_maps[node_type][node_hash] = node

        return node

    def to_xml(
        self, out_file: str = None, nsmap: dict = None, indent: str = "  "
    ) -> etree.Element:
        """Convert a document tree (nested dict) into an XML file

        Args:
            out_file: If provided, write output to a file.
            nsmap: An optional namespace mapping.
            indent: A string used as indentin XML output.

        Returns:
            The etree object corresponding to the root XML node.
        """
        doc = self._make_xml_node(
            self.document_tree,
            self.model.tables[self.document_tree["type"]].name,
            nsmap,
        )
        if self.model.tables[self.model.root_table].is_virtual_node:
            child = None
            for child in doc:
                break
            doc = child
        if out_file:
            etree.indent(doc, space=indent)
            with open(out_file, "wt") as f:
                f.write(
                    etree.tostring(
                        doc,
                        pretty_print=True,
                        encoding="utf-8",
                        xml_declaration=True,
                    ).decode("utf-8")
                )
        return doc

    def _make_xml_node(self, node_data, node_name, nsmap: dict = None):
        def check_transformed_node(node_type, element):
            """Convert "choice" transformed nodes (type/value) to `<type>value</type>` XML nodes"""
            if (
                node_type in self.model.types_transforms
                and self.model.types_transforms[node_type] == "choice"
            ):
                new_node = etree.Element(element.tag)
                extracted = {}
                for child in element:
                    extracted[child.tag] = child.text
                if "type" in extracted and "value" in extracted:
                    child_node = etree.Element(extracted["type"])
                    child_node.text = extracted["value"]
                    new_node.append(child_node)
                    return new_node
                else:
                    return None
            return element

        tb = self.model.tables[node_data["type"]]
        # due to "elevated" nodes (i.e. flattened), we need to build a stack of nested nodes to reconstruct the
        # original XML. It is a list of tuples of (node type, node Element).
        nodes_stack = [(node_data["type"], etree.Element(node_name, nsmap=nsmap))]
        prev_chain = []
        prev_ngroup = None
        ngroup_stack = []
        for field_type, rel_name, rel in tb.fields:
            # This part manages the nodes stack, based on `name_chain` attribute which represents a "path".
            # We compare the current path with the previous field path, and manage the nodes stack accordingly
            # (i.e. create new nested nodes, pop the last node when moving to another path, etc.)
            name_chain = rel.name_chain[:-1]
            i = len(prev_chain)
            while i > 0 and (
                i > len(name_chain) or name_chain[i - 1][0] != prev_chain[i - 1][0]
            ):
                completed_node = check_transformed_node(*nodes_stack.pop())
                if completed_node is not None and (
                    len(completed_node) > 0
                    or completed_node.text
                    or len(completed_node.attrib) > 0
                ):
                    nodes_stack[-1][1].append(completed_node)
                i -= 1
            while i < len(name_chain):
                node = etree.Element(name_chain[i][0])
                nodes_stack.append(
                    (
                        name_chain[i][1],
                        node,
                    )
                )
                i += 1
            prev_chain = name_chain
            children = []
            attributes = {}
            text_content = None
            if field_type == "col":
                if rel_name in node_data["content"]:
                    if rel.is_attr:
                        attributes[rel.name_chain[-1][0]] = node_data["content"][
                            rel_name
                        ][0]
                    elif rel.is_content:
                        text_content = node_data["content"][rel_name][0]
                    else:
                        for field_value in node_data["content"][rel_name]:
                            child = etree.Element(rel.name_chain[-1][0])
                            if isinstance(field_value, datetime):
                                field_value = field_value.isoformat()
                            child.text = str(field_value).encode("utf-8")
                            children.append(child)
            elif field_type == "rel1":
                if rel_name in node_data["content"]:
                    child = self._make_xml_node(
                        node_data["content"][rel_name][0], rel.name_chain[-1][0]
                    )
                    children = [child]
            elif field_type == "reln":
                if rel_name in node_data["content"]:
                    children = [
                        self._make_xml_node(child_tree, rel.name_chain[-1][0])
                        for child_tree in node_data["content"][rel_name]
                    ]
            if prev_ngroup and rel.ngroup != prev_ngroup:
                for ngroup_children in zip_longest(*ngroup_stack):
                    for child in ngroup_children:
                        nodes_stack[-1][1].append(child)
                ngroup_stack = []
            prev_ngroup = rel.ngroup
            if len(children) > 0:
                if rel.ngroup:
                    ngroup_stack.append(children)
                else:
                    for child in children:
                        nodes_stack[-1][1].append(child)
            for key, val in attributes.items():
                nodes_stack[-1][1].set(key, val)
            if text_content is not None:
                nodes_stack[-1][1].text = text_content
        if len(ngroup_stack) > 0:
            for ngroup_children in zip_longest(*ngroup_stack):
                for child in ngroup_children:
                    nodes_stack[-1][1].append(child)
        while len(nodes_stack) > 1:
            node = check_transformed_node(*nodes_stack.pop())
            if node is not None and len(node) > 0:
                nodes_stack[-1][1].append(node)

        return check_transformed_node(*nodes_stack[0])
