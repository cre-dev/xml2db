import os
import pprint

import pytest
from lxml import etree

from xml2db import DataModel
from xml2db.xml_converter import XMLConverter, remove_record_hash
from .conftest import list_xml_path, models_path
from .sample_models import models


@pytest.mark.parametrize(
    "test_config",
    [
        {**model, **version, "xml_file": xml_file}
        for model in models
        for xml_file in list_xml_path(model, "xml")
        + list_xml_path(model, "equivalent_xml")
        for version in model["versions"]
    ],
)
def test_iterative_recursive_parsing(test_config):
    """Test whether iterative and recursive parsing give same results"""
    model = DataModel(
        str(os.path.join(models_path, test_config["id"], test_config["xsd"])),
        short_name=test_config["id"],
        model_config=test_config["config"],
    )
    converter = XMLConverter(model)
    file_path = test_config["xml_file"]

    parsed_recursive = converter.parse_xml(
        file_path, file_path, skip_validation=True, iterparse=False
    )
    parsed_iterative = converter.parse_xml(
        file_path, file_path, skip_validation=True, iterparse=True
    )

    assert parsed_recursive == parsed_iterative


@pytest.mark.parametrize(
    "test_config",
    [
        {**model, **version, "xml_file": xml_file}
        for model in models
        for xml_file in list_xml_path(model, "xml")
        for version in model["versions"]
    ],
)
def test_document_tree_to_flat_data(test_config):
    """A test for document tree to flat data conversion and back"""

    model = DataModel(
        str(os.path.join(models_path, test_config["id"], test_config["xsd"])),
        short_name=test_config["id"],
        model_config=test_config["config"],
    )
    converter = XMLConverter(model)

    file_path = test_config["xml_file"]

    # parse XML to document tree
    converter.parse_xml(file_path, file_path)
    exp_doc_tree = pprint.pformat(remove_record_hash(converter.document_tree))

    # parse XML to document tree and then flat data model
    doc = model.parse_xml(file_path)
    # and convert it back to document tree
    act_doc_tree = pprint.pformat(doc.flat_data_to_doc_tree())

    assert act_doc_tree == exp_doc_tree


@pytest.mark.parametrize(
    "test_config",
    [
        {**model, **version, "xml_file": xml_file}
        for model in models
        for xml_file in list_xml_path(model, "xml")
        for version in model["versions"]
    ],
)
def test_document_tree_to_xml(test_config):
    """A test for document tree to xml conversion and back"""

    model = DataModel(
        str(os.path.join(models_path, test_config["id"], test_config["xsd"])),
        short_name=test_config["id"],
        model_config=test_config["config"],
    )
    converter = XMLConverter(model)

    file_path = test_config["xml_file"]

    # parse XML to document tree
    converter.parse_xml(file_path, file_path)

    # convert it back to XML, copying namespace and root attributes from original XML
    src = etree.parse(file_path).getroot()
    el = converter.to_xml(nsmap=src.nsmap)
    for key, val in src.attrib.items():
        el.set(key, val)

    xml = etree.tostring(
        el,
        pretty_print=True,
        encoding="utf-8",
        xml_declaration=True,
    ).decode("utf-8")

    # compare with source XML file as text
    with open(file_path, "rt") as f:
        ref_xml = f.read()

    assert xml == ref_xml


@pytest.mark.parametrize(
    "test_config",
    [
        {**model, **version}
        for model in models
        for version in model["versions"]
        if os.path.isdir(os.path.join(models_path, model["id"], "equivalent_xml"))
    ],
)
def test_equivalent_xml(test_config):
    """A test for xml documents which should result in the same extracted data"""

    xml_files = list_xml_path(test_config, "equivalent_xml")

    if len(xml_files) > 1:
        model = DataModel(
            str(os.path.join(models_path, test_config["id"], test_config["xsd"])),
            short_name=test_config["id"],
            model_config=test_config["config"],
        )
        ref_data = model.parse_xml(xml_files[0])
        for xml_file in xml_files[1:]:
            equ_data = model.parse_xml(xml_file)
            assert ref_data.data == equ_data.data
