"""Tests for concurrent XML loading with multiprocessing and a file-based DuckDB."""
import multiprocessing
import os
import tempfile

import pytest

pytest.importorskip("duckdb", reason="duckdb not installed")

from sqlalchemy import create_engine, text

from xml2db import DataModel

_SAMPLE = os.path.join(os.path.dirname(__file__), "sample_models", "orders")
_XSD = os.path.join(_SAMPLE, "orders.xsd")
_XML_FILES = [
    os.path.join(_SAMPLE, "xml", f"order{i}.xml") for i in (1, 2, 3)
]


def _load_xml_file(xml_path: str, xsd_path: str, db_path: str, lock) -> None:
    """Worker function: parse one XML file and load it into a shared DuckDB file.

    Each process builds its own DataModel (and gets a unique temp_prefix UUID),
    so temporary tables never collide.  All database I/O is serialised via *lock*
    because DuckDB allows only one active writer at a time.
    """
    model = DataModel(
        xsd_file=xsd_path,
        connection_string=f"duckdb:///{db_path}",
    )
    # CPU-bound XML parsing runs in parallel across processes.
    doc = model.parse_xml(xml_path)

    # Serialise all database access: one writer at a time for DuckDB.
    with lock:
        doc.insert_into_target_tables()
        # Dispose inside the lock so the file handle is released before
        # the next process tries to open the database.
        model.engine.dispose()


def test_multiprocessing_file_duckdb():
    """Three worker processes load XML files concurrently into a file-based DuckDB.

    Parsing happens in parallel; database writes are serialised via a
    multiprocessing.Lock.  After all workers finish, the target table must
    contain one row per XML file (each file has a distinct batch_id, so no
    deduplication occurs).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.duckdb")
        lock = multiprocessing.Lock()

        processes = [
            multiprocessing.Process(
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

        engine = create_engine(f"duckdb:///{db_path}")
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
        engine.dispose()

        assert count == len(_XML_FILES)
