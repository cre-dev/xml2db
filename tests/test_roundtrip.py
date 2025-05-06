import os

import pytest
from lxml import etree

from xml2db.xml_converter import XMLConverter, remove_record_hash
from .conftest import list_xml_path
from .sample_models import models

import re
import tzlocal 
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Tuple

# Regex for ISO-like datetime with timezone (adjust as needed)
IANA_TZ = str(tzlocal.get_localzone())
DATE_PATTERN = re.compile(
    r'(\d{2}|\d{4})-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}\.\d{3}(?:[+-]\d{2}:\d{2}|Z)'
)
TIME_ZONE = os.environ.get("TIME_ZONE", IANA_TZ)

def convert_date_string(date_str: str, to_tz: str) -> str:
    # Normalize 'Z' to '+00:00'
    if date_str.endswith('Z'):
        date_str = date_str[:-1] + '+00:00'

    year = 0
    try:
        dt = datetime.strptime(date_str, '%y-%m-%dT%H:%M:%S.%f%z')
        year = 2
    except:
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f%z')
            year = 4
        except:
            pass
    
    formatted = date_str
    if year > 0:
        # Convert to your desired timezone (example: US/Mountain)
        target_tz = ZoneInfo(to_tz)
        dt_new = dt.astimezone(target_tz)

        # Format back to original string format
        if year == 2:
            formatted = dt_new.strftime('%y-%m-%dT%H:%M:%S.%f%z')
        elif year == 4:
            formatted = dt_new.strftime('%Y-%m-%dT%H:%M:%S.%f%z')

        # Insert colon in timezone offset for ISO 8601 compliance
        formatted = formatted[:-2] + ':' + formatted[-2:]
        # Truncate microseconds to milliseconds
        dot_idx = formatted.find('.')
        if dot_idx != -1:
            formatted = formatted[:dot_idx+4] + formatted[dot_idx+7:]

    return formatted
    
def update_dates_in_tuple(data: Tuple[str, Any], to_tz: str) -> Tuple[str, Any]:
    def update_dates(obj: Any, to_tz: str) -> Any:
        if isinstance(obj, dict):
            return {k: update_dates(v, to_tz) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [update_dates(item, to_tz) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(update_dates(item, to_tz) for item in obj)
        elif isinstance(obj, str) and DATE_PATTERN.match(obj):
            try:
                return convert_date_string(obj, to_tz)
            except Exception:
                return obj
        else:
            return obj

    key, nested_dict = data
    updated_dict = update_dates(nested_dict, to_tz)
    return (key, updated_dict)

def convert(match, tz=TIME_ZONE):
    date_str = match.group()
    return convert_date_string(date_str=date_str, to_tz=tz)

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
            f"input_file_path='{file}'", force_tz=TIME_ZONE
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
        xml = re.sub(DATE_PATTERN, convert, xml)
        ref_xml = re.sub(DATE_PATTERN, convert, ref_xml)
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
            f"input_file_path='{file}'", force_tz=TIME_ZONE
        )

        # parse file to doctree for reference
        converter = XMLConverter(model)
        converter.parse_xml(file, file)

        assert update_dates_in_tuple(doc.flat_data_to_doc_tree(), TIME_ZONE) == update_dates_in_tuple(remove_record_hash(
            converter.document_tree
        ), TIME_ZONE)


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
            f"input_file_path='{file}'", force_tz=TIME_ZONE
        )

        # parse file to doctree for reference
        converter = XMLConverter(model)
        converter.parse_xml(file, file)

        assert update_dates_in_tuple(doc.flat_data_to_doc_tree(), TIME_ZONE) == update_dates_in_tuple(remove_record_hash(
            converter.document_tree
        ), TIME_ZONE)


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
        f"input_file_path='{file_path}'", force_tz=TIME_ZONE
    )

    # parse file to doctree for reference
    converter = XMLConverter(model)
    converter.parse_xml(file_path, file_path)

    assert update_dates_in_tuple(doc.flat_data_to_doc_tree(), TIME_ZONE) == update_dates_in_tuple(remove_record_hash(
        converter.document_tree
    ), TIME_ZONE)
