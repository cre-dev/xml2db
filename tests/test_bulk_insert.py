"""Unit tests for dialect bulk_insert implementations."""
import datetime

import pytest

pytest.importorskip("duckdb", reason="duckdb not installed")

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Double,
    Integer,
    LargeBinary,
    MetaData,
    SmallInteger,
    String,
    Table,
    create_engine,
    select,
    text,
)

from xml2db.dialect.base import DatabaseDialect
from xml2db.dialect.duckdb import DuckDBDialect


@pytest.fixture()
def duckdb_engine():
    return create_engine("duckdb:///:memory:")


def _make_table(engine, name, *extra_cols):
    """Create a simple test table and return the SQLAlchemy Table object."""
    meta = MetaData()
    table = Table(
        name,
        meta,
        Column("id", Integer, key="id"),
        Column("label", String(100), key="label"),
        *extra_cols,
    )
    meta.create_all(engine)
    return table


def _roundtrip(engine, table, records):
    """Insert records via DuckDBDialect.bulk_insert and read them back."""
    dialect = DuckDBDialect()
    with engine.begin() as conn:
        dialect.bulk_insert(conn, table, records)
    with engine.connect() as conn:
        return conn.execute(select(table)).mappings().all()


# ---------------------------------------------------------------------------
# Base dialect falls back to SQLAlchemy executemany
# ---------------------------------------------------------------------------


def test_base_dialect_bulk_insert(duckdb_engine):
    table = _make_table(duckdb_engine, "base_test")
    records = [{"id": 1, "label": "hello"}, {"id": 2, "label": "world"}]
    DatabaseDialect().bulk_insert(
        duckdb_engine.connect().__enter__(), table, records
    )
    # Just check the method is importable and has the right signature.


# ---------------------------------------------------------------------------
# DuckDB dialect: basic types
# ---------------------------------------------------------------------------


def test_duckdb_bulk_insert_basic(duckdb_engine):
    table = _make_table(duckdb_engine, "basic")
    records = [{"id": 1, "label": "hello"}, {"id": 2, "label": None}]
    rows = _roundtrip(duckdb_engine, table, records)
    assert len(rows) == 2
    assert rows[0]["id"] == 1
    assert rows[0]["label"] == "hello"
    assert rows[1]["label"] is None


def test_duckdb_bulk_insert_numeric_types(duckdb_engine):
    meta = MetaData()
    table = Table(
        "numeric_types",
        meta,
        Column("i", Integer, key="i"),
        Column("bi", BigInteger, key="bi"),
        Column("si", SmallInteger, key="si"),
        Column("d", Double, key="d"),
    )
    meta.create_all(duckdb_engine)
    records = [{"i": 1, "bi": 10**15, "si": 32767, "d": 3.14}]
    rows = _roundtrip(duckdb_engine, table, records)
    assert rows[0]["i"] == 1
    assert rows[0]["bi"] == 10**15
    assert rows[0]["si"] == 32767
    assert abs(rows[0]["d"] - 3.14) < 1e-9


def test_duckdb_bulk_insert_boolean(duckdb_engine):
    meta = MetaData()
    table = Table(
        "bool_test",
        meta,
        Column("id", Integer, key="id"),
        Column("flag", Boolean, key="flag"),
    )
    meta.create_all(duckdb_engine)
    records = [{"id": 1, "flag": True}, {"id": 2, "flag": False}, {"id": 3, "flag": None}]
    rows = _roundtrip(duckdb_engine, table, records)
    assert rows[0]["flag"] is True
    assert rows[1]["flag"] is False
    assert rows[2]["flag"] is None


def test_duckdb_bulk_insert_datetime(duckdb_engine):
    meta = MetaData()
    table = Table(
        "dt_test",
        meta,
        Column("id", Integer, key="id"),
        Column("ts", DateTime(timezone=True), key="ts"),
    )
    meta.create_all(duckdb_engine)
    dt = datetime.datetime(2023, 9, 27, 14, 35, 54, 274602)
    records = [{"id": 1, "ts": dt}, {"id": 2, "ts": None}]
    rows = _roundtrip(duckdb_engine, table, records)
    # Value must survive the CSV round-trip and be returned as a datetime-like object.
    assert rows[0]["ts"] is not None
    assert rows[1]["ts"] is None


def test_duckdb_bulk_insert_binary(duckdb_engine):
    meta = MetaData()
    table = Table(
        "binary_test",
        meta,
        Column("id", Integer, key="id"),
        Column("hash", LargeBinary(32), key="hash"),
    )
    meta.create_all(duckdb_engine)
    payload = b"\xde\xad\xbe\xef" * 8
    records = [{"id": 1, "hash": payload}, {"id": 2, "hash": None}]
    rows = _roundtrip(duckdb_engine, table, records)
    assert bytes(rows[0]["hash"]) == payload
    assert rows[1]["hash"] is None


def test_duckdb_bulk_insert_scalar_column_default(duckdb_engine):
    """Columns with Python-side scalar defaults absent from records must be applied."""
    meta = MetaData()
    table = Table(
        "default_test",
        meta,
        Column("id", Integer, key="id"),
        Column("flag", Boolean, default=False, key="flag"),
    )
    meta.create_all(duckdb_engine)
    # Records do NOT contain 'flag'; the default must be applied.
    records = [{"id": 1}, {"id": 2}]
    rows = _roundtrip(duckdb_engine, table, records)
    assert rows[0]["flag"] is False
    assert rows[1]["flag"] is False


def test_duckdb_bulk_insert_quoted_csv_field_after_large_unquoted_sample(duckdb_engine):
    """Regression: DuckDB's CSV sniffer uses only the first ~20k rows as a sample.

    If all sampled rows are unquoted, the sniffer sets quote=(empty), causing a
    column-count error when it later hits a row whose cell value contains a comma
    (making csv.writer emit a quoted field).  Explicitly passing quote='"' to
    read_csv bypasses auto-detection and must always be present.
    """
    table = _make_table(duckdb_engine, "quoted_field_test")
    # 'vals' value that contains a comma — document.py's 'join' transform can produce
    # strings like '"val,ue",other' which csv.writer then wraps in outer quotes,
    # yielding a quoted CSV cell.
    problematic_value = '"val,ue",other_value'
    records = [
        {"id": i, "label": "simple"} for i in range(25_000)  # exceeds sniffer sample
    ] + [{"id": 25_000, "label": problematic_value}]
    rows = _roundtrip(duckdb_engine, table, records)
    assert len(rows) == 25_001
    assert rows[-1]["label"] == problematic_value


def test_duckdb_bulk_insert_empty(duckdb_engine):
    table = _make_table(duckdb_engine, "empty_test")
    dialect = DuckDBDialect()
    with engine.begin() if False else duckdb_engine.begin() as conn:
        dialect.bulk_insert(conn, table, [])
    with duckdb_engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM empty_test")).scalar()
    assert count == 0
