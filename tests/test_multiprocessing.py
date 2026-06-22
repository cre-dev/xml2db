"""Tests for concurrent XML loading with multiprocessing and a file-based DuckDB."""
import multiprocessing
import os
import tempfile

import pytest
from lxml import etree

pytest.importorskip("duckdb", reason="duckdb not installed")

from sqlalchemy import String, create_engine, text

from xml2db import DataModel

_SAMPLE = os.path.join(os.path.dirname(__file__), "sample_models", "orders")
_XSD = os.path.join(_SAMPLE, "orders.xsd")
_XML_FILES = [
    os.path.join(_SAMPLE, "xml", f"order{i}.xml") for i in (1, 2, 3)
]

# Matches orders model version 0 in sample_models/models.py so that the XML
# roundtrip produces byte-for-byte identical output.
_MODEL_CONFIG = {
    "tables": {
        "shiporder": {"fields": {"orderperson": {"transform": False}}},
        "item": None,
    },
    "record_hash_column_name": "record_hash",
    "metadata_columns": [
        {"name": "input_file_path", "type": String(256)},
    ],
}


def _load_xml_file(xml_path: str, xsd_path: str, db_path: str, lock) -> None:
    """Worker function: parse one XML file and load it into a shared DuckDB file.

    Each process builds its own DataModel (and gets a unique temp_prefix UUID),
    so temporary tables never collide.  All database I/O is serialised via *lock*
    because DuckDB allows only one active writer at a time.
    """
    model = DataModel(
        xsd_file=xsd_path,
        connection_string=f"duckdb:///{db_path}",
        model_config=_MODEL_CONFIG,
    )
    # CPU-bound XML parsing runs in parallel across processes.
    doc = model.parse_xml(xml_path, metadata={"input_file_path": xml_path})

    # Serialise all database access: one writer at a time for DuckDB.
    with lock:
        doc.insert_into_target_tables()
        # Dispose inside the lock so the file handle is released before
        # the next process tries to open the database.
        model.engine.dispose()


def test_multiprocessing_file_duckdb():
    """Three worker processes load XML files concurrently into a file-based DuckDB.

    Parsing happens in parallel; database writes are serialised via a
    multiprocessing.Lock.  After all workers finish:
    - the target table must contain one row per XML file, and
    - each file must round-trip back to identical XML (content assertion).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.duckdb")
        ctx = multiprocessing.get_context("spawn")
        lock = ctx.Lock()

        processes = [
            ctx.Process(
                target=_load_xml_file,
                args=(xml_path, _XSD, db_path, lock),
            )
            for xml_path in _XML_FILES
        ]
        for p in processes:
            p.start()
        for p in processes:
            p.join()
            assert p.exitcode == 0, (
                f"Worker for {_XML_FILES[processes.index(p)]} "
                f"exited with code {p.exitcode}"
            )

        # --- row count ---
        engine = create_engine(f"duckdb:///{db_path}")
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
        engine.dispose()
        assert count == len(_XML_FILES)

        # --- content roundtrip ---
        verify_model = DataModel(
            xsd_file=_XSD,
            connection_string=f"duckdb:///{db_path}",
            model_config=_MODEL_CONFIG,
        )
        for xml_path in _XML_FILES:
            doc = verify_model.extract_from_database(
                f"input_file_path='{xml_path}'",
                force_tz="Europe/Paris",
            )
            src = etree.parse(xml_path).getroot()
            el = doc.to_xml(nsmap=src.nsmap)
            for key, val in src.attrib.items():
                el.set(key, val)
            actual = etree.tostring(
                el, pretty_print=True, encoding="utf-8", xml_declaration=True
            ).decode("utf-8")
            with open(xml_path) as f:
                expected = f.read()
            assert actual == expected, f"XML roundtrip failed for {xml_path}"
        verify_model.engine.dispose()
