import typing
from datetime import datetime
from typing import Union
import logging
from lxml import etree
from io import BytesIO
from itertools import zip_longest

if typing.TYPE_CHECKING:
    from xml2db.model import DataModel

logger = logging.getLogger(__name__)


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
    ) -> dict:
        """Parse an XML document into a nested dict and performs the simplifications defined in the
        DataModel object ("pull" child to upper level, transform a choice model into "type" and "value"
        fields or concatenate children as string).

        Args:
            xml_file: An XML file path or file content to be converted
            file_path: The file path to be printed in logs
            skip_validation: Whether we should validate XML against the schema before parsing
            recover: Try to process malformed XML (lxml option)

        Returns:
            The parsed data in the document tree format (nested dict)
        """

        if skip_validation:
            logger.info("Skipping XML file validation")
        else:
            logger.info("Validating XML file against the schema")
            if not self.model.xml_schema.is_valid(xml_file):
                logger.error(f"XML file {file_path} does not conform with the schema")
                raise ValueError(
                    f"XML file {file_path} does not conform with the schema"
                )
            logger.info("XML file conforms with the schema")

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

        joined_values = False
        for event, element in etree.iterparse(
            xml_file, recover=recover, events=["start", "end"]
        ):
            key = element.tag.split("}")[1] if "}" in element.tag else element.tag
            if event == "start":
                node_type = None
                if nodes_stack[-1]["type"]:
                    node_type_key = (nodes_stack[-1]["type"], key)
                    joined_values = (
                        self.model.fields_transforms.get(
                            node_type_key,
                            (None, "join"),
                        )[1]
                        == "join"
                    )
                    if not joined_values:
                        node_type = self.model.fields_transforms[node_type_key][0]
                else:
                    node_type = self.model.root_table
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
                if joined_values:  # joined_values was set with the previous "start" event just before
                    if element.text and element.text.strip():
                        if key in nodes_stack[-1]["content"]:
                            nodes_stack[-1]["content"][key].append(element.text)
                        else:
                            nodes_stack[-1]["content"][key] = [element.text]
                else:
                    node = nodes_stack.pop()
                    if element.text and element.text.strip():
                        node["content"]["value"] = [element.text.strip()]
                    self._transform_node(node)
                    if key in nodes_stack[-1]["content"]:
                        nodes_stack[-1]["content"][key].append(node)
                    else:
                        nodes_stack[-1]["content"][key] = [node]
                joined_values = False

        # return the outer container only if root table is a "virtual" node, else return the XML root node
        if nodes_stack[0]["type"]:
            res = nodes_stack[0]
            self._transform_node(res)
            self.document_tree = res
            return res
        for k, v in nodes_stack[0]["content"].items():
            self.document_tree = v[0]
            return self.document_tree

    def _transform_node(self, node):
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
