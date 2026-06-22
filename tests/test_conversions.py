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


def test_field_rename():
    """Test that 'rename' in field config sets the physical DB column name without affecting internal logic"""
    model = DataModel(
        str(os.path.join(models_path, "orders", "orders.xsd")),
        model_config={
            "tables": {
                "shiporder": {
                    "fields": {
                        "orderid": {"rename": "order_id"},
                    }
                }
            }
        },
    )
    shiporder_table = model.tables["shipordertype"]

    # physical column name in the DB uses the renamed value
    assert shiporder_table.table.c["orderid"].name == "order_id"
    # temp table should also use the renamed physical name
    assert shiporder_table.temp_table.c["orderid"].name == "order_id"

    # parsing still works and data dict uses the original logical name
    doc = model.parse_xml(str(os.path.join(models_path, "orders", "xml", "order1.xml")))
    records = doc.data["shipordertype"]["records"]
    assert len(records) > 0
    assert "orderid" in records[0]


def test_field_skip_column():
    """Test that transform='skip' removes a scalar column from the schema and parsed records"""
    model = DataModel(
        str(os.path.join(models_path, "orders", "orders.xsd")),
        model_config={
            "tables": {
                "item": {
                    "fields": {
                        "note": {"transform": "skip"},
                    }
                }
            }
        },
    )
    item_table = model.tables["itemtype"]

    # column must be absent from both the DataModelTable and the SQLAlchemy table
    assert "note" not in item_table.columns
    assert "note" not in item_table.table.c
    # neighbouring columns are unaffected
    assert "quantity" in item_table.table.c

    # parsing works; 'note' is absent from records even for files that contain <note>
    doc = model.parse_xml(str(os.path.join(models_path, "orders", "xml", "order1.xml")))
    records = doc.data["itemtype"]["records"]
    assert len(records) > 0
    assert "note" not in records[0]


def test_field_skip_relation():
    """Test that transform='skip' on a relation removes its generated columns and prunes the child table"""
    model = DataModel(
        str(os.path.join(models_path, "orders", "orders.xsd")),
        model_config={
            "tables": {
                "item": {
                    "fields": {
                        "delivery": {"transform": "skip"},
                    }
                }
            }
        },
    )
    item_table = model.tables["itemtype"]

    # delivery is a rel1 that would normally be elevated → its FK columns must be absent
    assert "delivery_from_fk_orderperson" not in item_table.table.c
    assert "delivery_to_fk_orderperson" not in item_table.table.c
    # 'delivery' is also absent from relations_1 (no FK column, no merge statements)
    assert "delivery" not in item_table.relations_1

    # deliveryType has no other parents, so it should be pruned from the model
    assert "deliveryType" not in model.tables

    # parsing works even for XML files that contain <delivery>; delivery data is silently dropped
    doc = model.parse_xml(str(os.path.join(models_path, "orders", "xml", "order3.xml")))
    records = doc.data["itemtype"]["records"]
    assert len(records) > 0
    assert all("delivery" not in key for key in records[0])


@pytest.mark.dbtest
def test_field_skip_db(conn_string):
    """Test that skipped fields do not cause DB errors during insert"""
    model = DataModel(
        str(os.path.join(models_path, "orders", "orders.xsd")),
        connection_string=conn_string,
        db_schema="test_xml2db_skip",
        model_config={
            "tables": {
                "item": {
                    "fields": {
                        "note": {"transform": "skip"},
                    }
                }
            }
        },
    )
    model.create_db_schema()
    model.drop_all_tables()
    model.create_all_tables()
    try:
        # insert a file that contains <note> — must succeed without errors
        xml_path = str(os.path.join(models_path, "orders", "xml", "order1.xml"))
        doc = model.parse_xml(xml_path)
        doc.insert_into_target_tables()
    finally:
        model.drop_all_tables()


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
