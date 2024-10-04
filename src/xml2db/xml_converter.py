import typing
from datetime import datetime
from typing import Union
import logging
from lxml import etree
from io import BytesIO
from itertools import zip_longest


if typing.TYPE_CHECKING:
    from .model import DataModel

logger = logging.getLogger(__name__)


def remove_record_hash(node) -> tuple:
    """Remove hash data recursively from document tree. Only used for tests, in order to compare document trees with
    data extracted from the database (which does not always store record hash).

    Args:
        node: a node from the document tree
    """
    node_type, content, _ = node
    content = {
        key: [
            (remove_record_hash(child) if isinstance(child, tuple) else child)
            for child in val
        ]
        for key, val in content.items()
    }
    return node_type, content


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
    ) -> tuple:
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
        if not iterparse or (not skip_validation and recover):
            logger.info("Parsing XML file")
            xt = etree.parse(xml_file, parser=etree.XMLParser(recover=recover))

        if skip_validation:
            logger.info("Skipping XML file validation")
        else:
            logger.info("Validating XML file against the schema")
            if not self.model.lxml_schema.validate(xt if xt else etree.parse(xml_file)):
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

    def _parse_element_tree(self, xt: etree.ElementTree) -> tuple:
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
    ) -> tuple:
        """Parse nodes of an XML document into a dict recursively

        Args:
            node_type: type of the node to parse
            node: lxml node object
            compute_hash: should we compute hash and deduplicate?
            hash_maps: a dict referencing nodes based on their hash

        Returns:
            A tuple of node_type, content (dict), hash
        """

        content = {}

        for key, val in node.attrib.items():
            if (
                key
                != "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation"
            ):
                content[key] = [val]

        if node.text and node.text.strip():
            content["value"] = [node.text.strip()]

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
            if key in content:
                content[key].append(value)
            else:
                content[key] = [value]

        node = self._transform_node(node_type, content)

        if compute_hash:
            return self._compute_hash_deduplicate(node, hash_maps)

        return node

    def _parse_iterative(
        self, xml_file: Union[str, BytesIO], recover: bool = False
    ) -> tuple:
        """Parse an XML file into a document tree (nested dict) in an iterative fashion.

        This method uses etree.iterparse and does not load the entire XML document in memory.
        It saves memory, especially if you decide to filter out nodes using 'document_tree_node_hook' hook.

        Args:
            xml_file: an XML file to parse
            recover: should we try to parse incorrect XML?

        Returns:
            A tuple of node_type, content (dict), hash
        """
        nodes_stack = [
            (
                (
                    self.model.root_table
                    if self.model.tables[self.model.root_table].is_virtual_node
                    else None
                ),
                {},
            )
        ]
        hash_maps = {}

        joined_values = False
        for event, element in etree.iterparse(
            xml_file,
            recover=recover,
            events=["start", "end"],
            remove_blank_text=True,
        ):
            key = element.tag.split("}")[1] if "}" in element.tag else element.tag
            if event == "start":
                if nodes_stack[-1][0]:
                    node_type_key = (nodes_stack[-1][0], key)
                    node_type, transform = self.model.fields_transforms.get(
                        node_type_key, (None, "join")
                    )
                else:
                    node_type, transform = self.model.root_table, None
                joined_values = transform == "join"
                if not joined_values:
                    content = {}
                    for attrib_key, attrib_val in element.attrib.items():
                        if (
                            attrib_key
                            != "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation"
                        ):
                            content[attrib_key] = [attrib_val]
                    nodes_stack.append((node_type, content))

            elif event == "end":
                # joined_values was set with the previous "start" event just before
                if joined_values:
                    if element.text:
                        if key in nodes_stack[-1][1]:
                            nodes_stack[-1][1][key].append(element.text)
                        else:
                            nodes_stack[-1][1][key] = [element.text]
                else:
                    node = nodes_stack.pop()
                    if nodes_stack[-1][0]:
                        node_type_key = (nodes_stack[-1][0], key)
                        node_type, transform = self.model.fields_transforms.get(
                            node_type_key, (None, "join")
                        )
                    else:
                        node_type, transform = self.model.root_table, None
                    if element.text:
                        node[1]["value"] = [element.text]
                    node = self._transform_node(*node)
                    if transform not in ["elevate", "elevate_wo_prefix"]:
                        node = self._compute_hash_deduplicate(node, hash_maps)
                    if node:
                        if key in nodes_stack[-1][1]:
                            nodes_stack[-1][1][key].append(node)
                        else:
                            nodes_stack[-1][1][key] = [node]
                joined_values = False
                element.clear(keep_tail=True)

        # return the outer container only if root table is a "virtual" node, else return the XML root node
        if nodes_stack[0][0]:
            res = self._transform_node(*nodes_stack[0])
            return self._compute_hash_deduplicate(res, hash_maps)
        for k, v in nodes_stack[0][1].items():
            return v[0]

    def _transform_node(self, node_type: str, content: dict) -> tuple:
        """Apply transformations to a given node

        Args:
            node_type: The node type to transform
            content: The node content dict to transform

        Returns:
            A tuple of (node_type, content) for the transformed node
        """
        for key in list(content.keys()):
            node_type_key = (node_type, key)
            if node_type_key in self.model.fields_transforms:
                transform = self.model.fields_transforms[node_type_key][1]
                if transform == "elevate" or transform == "elevate_wo_prefix":
                    prefix = f"{key}_" if transform == "elevate" else ""
                    child_content = content[key][0][1]
                    del content[key]
                    for child_key, val in child_content.items():
                        content[f"{prefix}{child_key}"] = val

        if node_type in self.model.types_transforms:
            if self.model.types_transforms[node_type] == "choice":
                child_key, val = list(content.items())[0]
                content = {"type": [child_key], "value": val}

        return node_type, content

    def _compute_hash_deduplicate(self, node: tuple, hash_maps: dict) -> tuple:
        """
        A function to compute hash for a document tree node and deduplicate its content

        Args:
            node: A tuple of (node_type, content) representing a node
            hash_maps: A dict of dicts storing reference to deduplicated nodes keyed by their type and hash value

        Returns:
            A tuple of (node_type, content, hash) representing a node after deduplication
        """
        node_type, content = node
        table = self.model.tables[node_type]

        h = self.model.model_config["record_hash_constructor"]()
        for field_type, name, _ in table.fields:
            if field_type == "col":
                h.update(str(content.get(name, None)).encode("utf-8"))
            elif field_type == "rel1":
                h.update(content[name][0][2] if name in content else b"")
            elif field_type == "reln":
                h_children = [v[2] for v in content.get(name, [])]
                for h_child in sorted(h_children):
                    h.update(h_child)
        node_hash = h.digest()

        if node_type not in hash_maps:
            hash_maps[node_type] = {}

        if node_hash in hash_maps[node_type]:
            return hash_maps[node_type][node_hash]

        node = (node_type, content, node_hash)

        if self.model.model_config["document_tree_node_hook"] is not None:
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
            self.model.tables[self.document_tree[0]].name,
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

        if len(node_data) == 3:
            node_type, content, _ = node_data
        else:
            node_type, content = node_data

        tb = self.model.tables[node_type]
        # due to "elevated" nodes (i.e. flattened), we need to build a stack of nested nodes to reconstruct the
        # original XML. It is a list of tuples of (node type, node Element).
        nodes_stack = [(node_type, etree.Element(node_name, nsmap=nsmap))]
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
                if rel_name in content:
                    if rel.is_attr:
                        attributes[rel.name_chain[-1][0]] = content[rel_name][0]
                    elif rel.is_content:
                        text_content = content[rel_name][0]
                    else:
                        for field_value in content[rel_name]:
                            child = etree.Element(rel.name_chain[-1][0])
                            if isinstance(field_value, datetime):
                                field_value = field_value.isoformat()
                            child.text = str(field_value).encode("utf-8")
                            children.append(child)
            elif field_type == "rel1":
                if rel_name in content:
                    child = self._make_xml_node(
                        content[rel_name][0], rel.name_chain[-1][0]
                    )
                    children = [child]
            elif field_type == "reln":
                if rel_name in content:
                    children = [
                        self._make_xml_node(child_tree, rel.name_chain[-1][0])
                        for child_tree in content[rel_name]
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
