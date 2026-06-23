import os

import pytest
from lxml import etree

from xml2db import LoadStats, MergeStats
from xml2db.xml_converter import XMLConverter, remove_record_hash
from .conftest import list_xml_path, models_path
from .sample_models import models


@pytest.mark.dbtest
def test_load_stats(conn_string):
    """Test that insert_into_target_tables returns a LoadStats with correct structure"""
    from xml2db import DataModel
    import sqlalchemy

    model = DataModel(
        str(os.path.join(models_path, "orders", "orders.xsd")),
        connection_string=conn_string,
        db_schema="test_xml2db_stats",
        model_config={
            "metadata_columns": [{"name": "src", "type": sqlalchemy.String(256)}]
        },
    )
    model.create_db_schema()
    model.drop_all_tables()
    model.create_all_tables()
    xml_path = str(os.path.join(models_path, "orders", "xml", "order1.xml"))
    try:
        # first load
        doc = model.parse_xml(xml_path, metadata={"src": "a"})
        stats = doc.insert_into_target_tables()

        assert isinstance(stats, LoadStats)
        assert stats.inserted >= 0
        assert stats.existing == 0  # nothing pre-existing on first load
        assert stats.duration_temp_insert > 0
        assert stats.duration_merge > 0
        assert stats.duration_cleanup > 0

        # second load of same file; reused rows should be existing (backends that
        # report rowcount); on DuckDB both will be 0, which is also acceptable
        doc2 = model.parse_xml(xml_path, metadata={"src": "b"})
        stats2 = doc2.insert_into_target_tables()

        assert isinstance(stats2, LoadStats)
        assert stats2.inserted >= 0
        assert stats2.existing >= 0
        assert stats2.inserted + stats2.existing >= 0
        # where rowcount is supported: all reused records from the first load
        # are now existing; inserted should be 0 or very small
        if stats.inserted > 0:
            assert stats2.existing > 0
    finally:
        model.drop_all_tables()


@pytest.mark.dbtest
@pytest.mark.parametrize(
    "model_config",
    [{**model, **version} for model in models for version in model["versions"]],
)
def test_database_xml_roundtrip(setup_db_model, model_config):
    """A test for roundtrip insert to the database from and to XML"""

    model = setup_db_model
    xml_files = list_xml_path(model_config, "xml")

    for file in xml_files:
        # do parse and insert into the database
        doc = model.parse_xml(file, metadata={"input_file_path": file})
        doc.insert_into_target_tables()

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
    xml_files = list_xml_path(model_config, "xml")

    for file in xml_files:
        # do parse and insert into the database
        doc = model.parse_xml(file, metadata={"input_file_path": file})
        doc.insert_into_target_tables()

    for file in xml_files:
        doc = model.extract_from_database(
            f"input_file_path='{file}'", force_tz="Europe/Paris"
        )

        # parse file to doctree for reference
        converter = XMLConverter(model)
        converter.parse_xml(file, file)

        assert doc.flat_data_to_doc_tree() == remove_record_hash(
            converter.document_tree
        )


@pytest.mark.dbtest
@pytest.mark.parametrize(
    "model_config",
    [{**models[0], **version} for version in models[0]["versions"]],
)
def test_database_document_tree_roundtrip_single_load(setup_db_model, model_config):
    """A test for roundtrip insert to the database from and to document tree"""

    model = setup_db_model
    xml_files = list_xml_path(model_config, "xml")

    flat_data = None
    doc = None
    for file in xml_files:
        # do parse
        doc = model.parse_xml(
            file, metadata={"input_file_path": file}, flat_data=flat_data
        )
        flat_data = doc.data

    # insert into the database all at once
    doc.insert_into_target_tables()

    for file in xml_files:
        doc = model.extract_from_database(
            f"input_file_path='{file}'", force_tz="Europe/Paris"
        )

        # parse file to doctree for reference
        converter = XMLConverter(model)
        converter.parse_xml(file, file)

        assert doc.flat_data_to_doc_tree() == remove_record_hash(
            converter.document_tree
        )


@pytest.mark.skip
@pytest.mark.parametrize(
    "model_config",
    [
        {**model, **version, "xml_file": xml_file}
        for model in models
        for xml_file in list_xml_path(model, "xml")
        for version in model["versions"]
    ],
)
def test_database_single_document_tree_roundtrip(setup_db_model, model_config):
    """A test for roundtrip insert to the database for a single file, useful for debugging but very slow"""

    model = setup_db_model
    file_path = os.path.join(model_config["xml_path"], model_config["xml_file"])

    # do parse and insert into the database
    doc = model.parse_xml(file_path, metadata={"input_file_path": file_path})
    doc.insert_into_target_tables()

    doc = model.extract_from_database(
        f"input_file_path='{file_path}'", force_tz="Europe/Paris"
    )

    # parse file to doctree for reference
    converter = XMLConverter(model)
    converter.parse_xml(file_path, file_path)

    assert doc.flat_data_to_doc_tree() == remove_record_hash(converter.document_tree)
