import os
import pytest
from lxml import etree
from xml2db.xml_converter import XMLConverter, remove_record_hash

from .fixtures import setup_db_model, conn_string
from .sample_models import models


@pytest.mark.dbtest
@pytest.mark.parametrize(
    "model_config",
    [{**model, **version} for model in models for version in model["versions"]],
)
def test_database_xml_roundtrip(setup_db_model, model_config):
    """A test for roundtrip insert to the database from and to XML"""

    model = setup_db_model
    xml_files = [
        os.path.join(model_config["xml_path"], file)
        for file in os.listdir(model_config["xml_path"])
    ]

    for file in xml_files:
        # do parse and insert into the database
        doc = model.parse_xml(file)
        doc.insert_into_target_tables(metadata={"input_file_path": file})

    for file in xml_files:
        doc = model.extract_from_database(
            f"input_file_path='{file}'", force_tz="Europe/Paris"
        )

        with open(file, "rt") as f:
            ref_xml = f.read()
        src = etree.parse(file).getroot()

        el = doc.to_xml(nsmap=src.nsmap)
        for key, val in src.attrib.items():
            el.set(key, val)

        xml = etree.tostring(
            el,
            pretty_print=True,
            encoding="utf-8",
            xml_declaration=True,
        ).decode("utf-8")

        assert xml == ref_xml


@pytest.mark.dbtest
@pytest.mark.parametrize(
    "model_config",
    [{**model, **version} for model in models for version in model["versions"]],
)
def test_database_document_tree_roundtrip(setup_db_model, model_config):
    """A test for roundtrip insert to the database from and to document tree"""

    model = setup_db_model
    xml_files = [
        os.path.join(model_config["xml_path"], file)
        for file in os.listdir(model_config["xml_path"])
    ]

    for file in xml_files:
        # do parse and insert into the database
        doc = model.parse_xml(file)
        doc.insert_into_target_tables(metadata={"input_file_path": file})

    for file in xml_files:
        doc = model.extract_from_database(
            f"input_file_path='{file}'", force_tz="Europe/Paris"
        )

        # parse file to doctree for reference
        converter = XMLConverter(model)
        converter.parse_xml(file, file)
        remove_record_hash(converter.document_tree)

        assert doc.flat_data_to_doc_tree() == converter.document_tree


@pytest.mark.skip
@pytest.mark.parametrize(
    "model_config",
    [
        {**model, **version, "xml_file": xml_file}
        for model in models
        for xml_file in os.listdir(model["xml_path"])
        for version in model["versions"]
    ],
)
def test_database_single_document_tree_roundtrip(setup_db_model, model_config):
    """A test for roundtrip insert to the database for a single file, useful for debugging but very slow"""

    model = setup_db_model
    file_path = os.path.join(model_config["xml_path"], model_config["xml_file"])

    # do parse and insert into the database
    doc = model.parse_xml(file_path)
    doc.insert_into_target_tables(metadata={"input_file_path": file_path})

    doc = model.extract_from_database(
        f"input_file_path='{file_path}'", force_tz="Europe/Paris"
    )

    # parse file to doctree for reference
    converter = XMLConverter(model)
    converter.parse_xml(file_path, file_path)
    remove_record_hash(converter.document_tree)

    assert doc.flat_data_to_doc_tree() == converter.document_tree
