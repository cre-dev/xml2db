"""Integration tests for MySQLDialect.bulk_insert (LOAD DATA LOCAL INFILE)."""
import datetime
import os

import pytest
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
)
from sqlalchemy.engine import make_url

from xml2db.dialect.mysql import MySQLDialect


def _make_mysql_engine():
    db_string = os.getenv("DB_STRING", "")
    if not db_string:
        pytest.skip("DB_STRING not set")
    url = make_url(db_string)
    if url.get_dialect().name not in ("mysql", "mariadb"):
        pytest.skip("DB_STRING is not a MySQL/MariaDB connection")
    driver = url.get_dialect().driver
    if driver == "pymysql":
        pytest.importorskip("pymysql")
    elif driver == "mysqldb":
        pytest.importorskip("MySQLdb")
    return create_engine(url, connect_args={"local_infile": True})


@pytest.fixture(scope="module")
def mysql_engine():
    engine = _make_mysql_engine()
    yield engine
    engine.dispose()


def _make_table(engine, name, *extra_cols):
    meta = MetaData()
    table = Table(
        name,
        meta,
        Column("id", Integer, key="id"),
        Column("label", String(200), key="label"),
        *extra_cols,
    )
    meta.create_all(engine)
    return table, meta


def _roundtrip(engine, table, records, **bulk_insert_kwargs):
    dialect = MySQLDialect()
    with engine.begin() as conn:
        dialect.bulk_insert(conn, table, records, **bulk_insert_kwargs)
    with engine.connect() as conn:
        q = select(table)
        if "id" in table.c:
            q = q.order_by(table.c.id)
        return conn.execute(q).mappings().all()


def _drop(meta, engine):
    meta.drop_all(engine)


# ---------------------------------------------------------------------------
# Basic types
# ---------------------------------------------------------------------------


@pytest.mark.dbtest
def test_mysql_bulk_insert_basic(mysql_engine):
    table, meta = _make_table(mysql_engine, "mysql_bi_basic")
    try:
        records = [{"id": 1, "label": "hello"}, {"id": 2, "label": None}]
        rows = _roundtrip(mysql_engine, table, records)
        assert len(rows) == 2
        assert rows[0]["label"] == "hello"
        assert rows[1]["label"] is None
    finally:
        _drop(meta, mysql_engine)


@pytest.mark.dbtest
def test_mysql_bulk_insert_empty(mysql_engine):
    table, meta = _make_table(mysql_engine, "mysql_bi_empty")
    try:
        dialect = MySQLDialect()
        with mysql_engine.begin() as conn:
            dialect.bulk_insert(conn, table, [])
        with mysql_engine.connect() as conn:
            count = len(conn.execute(select(table)).fetchall())
        assert count == 0
    finally:
        _drop(meta, mysql_engine)


@pytest.mark.dbtest
def test_mysql_bulk_insert_string_special_chars(mysql_engine):
    """Strings with backslashes, tabs, and newlines survive the round-trip."""
    table, meta = _make_table(mysql_engine, "mysql_bi_special")
    try:
        records = [
            {"id": 1, "label": "back\\slash"},
            {"id": 2, "label": "tab\there"},
            {"id": 3, "label": "new\nline"},
            {"id": 4, "label": "null-like \\N text"},
        ]
        rows = _roundtrip(mysql_engine, table, records)
        assert rows[0]["label"] == "back\\slash"
        assert rows[1]["label"] == "tab\there"
        assert rows[2]["label"] == "new\nline"
        assert rows[3]["label"] == "null-like \\N text"
    finally:
        _drop(meta, mysql_engine)


# ---------------------------------------------------------------------------
# Numeric types
# ---------------------------------------------------------------------------


@pytest.mark.dbtest
def test_mysql_bulk_insert_numeric_types(mysql_engine):
    meta = MetaData()
    table = Table(
        "mysql_bi_numeric",
        meta,
        Column("i", Integer, key="i"),
        Column("bi", BigInteger, key="bi"),
        Column("si", SmallInteger, key="si"),
        Column("d", Double, key="d"),
    )
    meta.create_all(mysql_engine)
    try:
        records = [{"i": 1, "bi": 10**15, "si": 32767, "d": 3.14}]
        rows = _roundtrip(mysql_engine, table, records)
        assert rows[0]["i"] == 1
        assert rows[0]["bi"] == 10**15
        assert rows[0]["si"] == 32767
        assert abs(rows[0]["d"] - 3.14) < 1e-9
    finally:
        meta.drop_all(mysql_engine)


# ---------------------------------------------------------------------------
# Boolean
# ---------------------------------------------------------------------------


@pytest.mark.dbtest
def test_mysql_bulk_insert_boolean(mysql_engine):
    meta = MetaData()
    table = Table(
        "mysql_bi_bool",
        meta,
        Column("id", Integer, key="id"),
        Column("flag", Boolean, key="flag"),
    )
    meta.create_all(mysql_engine)
    try:
        records = [
            {"id": 1, "flag": True},
            {"id": 2, "flag": False},
            {"id": 3, "flag": None},
        ]
        rows = _roundtrip(mysql_engine, table, records)
        assert rows[0]["flag"] is True
        assert rows[1]["flag"] is False
        assert rows[2]["flag"] is None
    finally:
        meta.drop_all(mysql_engine)


# ---------------------------------------------------------------------------
# DateTime
# ---------------------------------------------------------------------------


@pytest.mark.dbtest
def test_mysql_bulk_insert_datetime(mysql_engine):
    meta = MetaData()
    table = Table(
        "mysql_bi_dt",
        meta,
        Column("id", Integer, key="id"),
        Column("ts", DateTime, key="ts"),
    )
    meta.create_all(mysql_engine)
    try:
        dt = datetime.datetime(2023, 9, 27, 14, 35, 54)
        records = [{"id": 1, "ts": dt}, {"id": 2, "ts": None}]
        rows = _roundtrip(mysql_engine, table, records)
        assert rows[0]["ts"] is not None
        assert rows[1]["ts"] is None
    finally:
        meta.drop_all(mysql_engine)


# ---------------------------------------------------------------------------
# Binary (BLOB)
# ---------------------------------------------------------------------------


@pytest.mark.dbtest
def test_mysql_bulk_insert_binary(mysql_engine):
    meta = MetaData()
    table = Table(
        "mysql_bi_binary",
        meta,
        Column("id", Integer, key="id"),
        Column("data", LargeBinary, key="data"),
    )
    meta.create_all(mysql_engine)
    try:
        payload = b"\xde\xad\xbe\xef" * 8
        records = [{"id": 1, "data": payload}, {"id": 2, "data": None}]
        rows = _roundtrip(mysql_engine, table, records)
        assert bytes(rows[0]["data"]) == payload
        assert rows[1]["data"] is None
    finally:
        meta.drop_all(mysql_engine)


# ---------------------------------------------------------------------------
# Python-side scalar column defaults
# ---------------------------------------------------------------------------


@pytest.mark.dbtest
def test_mysql_bulk_insert_scalar_default(mysql_engine):
    meta = MetaData()
    table = Table(
        "mysql_bi_default",
        meta,
        Column("id", Integer, key="id"),
        Column("flag", Boolean, default=False, key="flag"),
    )
    meta.create_all(mysql_engine)
    try:
        records = [{"id": 1}, {"id": 2}]
        rows = _roundtrip(mysql_engine, table, records)
        assert rows[0]["flag"] is False
        assert rows[1]["flag"] is False
    finally:
        meta.drop_all(mysql_engine)


# ---------------------------------------------------------------------------
# bulk_load flag
# ---------------------------------------------------------------------------


@pytest.mark.dbtest
def test_mysql_bulk_load_true(mysql_engine):
    """bulk_load=True succeeds when local_infile is enabled on the engine."""
    from xml2db.dialect.mysql import _LOAD_DATA_THRESHOLD

    table, meta = _make_table(mysql_engine, "mysql_bi_bulk_load_true")
    try:
        records = [{"id": i, "label": f"row{i}"} for i in range(_LOAD_DATA_THRESHOLD)]
        rows = _roundtrip(mysql_engine, table, records, bulk_load=True)
        assert len(rows) == _LOAD_DATA_THRESHOLD
        assert rows[0]["label"] == "row0"
    finally:
        _drop(meta, mysql_engine)


@pytest.mark.dbtest
def test_mysql_bulk_load_false(mysql_engine):
    """bulk_load=False uses executemany even for large batches."""
    from xml2db.dialect.mysql import _LOAD_DATA_THRESHOLD

    table, meta = _make_table(mysql_engine, "mysql_bi_bulk_load_false")
    try:
        records = [{"id": i, "label": f"row{i}"} for i in range(_LOAD_DATA_THRESHOLD)]
        rows = _roundtrip(mysql_engine, table, records, bulk_load=False)
        assert len(rows) == _LOAD_DATA_THRESHOLD
    finally:
        _drop(meta, mysql_engine)


@pytest.mark.dbtest
def test_mysql_bulk_load_true_raises_without_local_infile(mysql_engine):
    """bulk_load=True raises RuntimeError when local_infile is not enabled."""
    from xml2db.dialect.mysql import _LOAD_DATA_THRESHOLD

    url = mysql_engine.url
    # Create an engine without local_infile so LOAD DATA LOCAL INFILE is rejected.
    engine_no_infile = create_engine(url)
    table, meta = _make_table(engine_no_infile, "mysql_bi_bulk_load_no_infile")
    try:
        records = [{"id": i, "label": f"row{i}"} for i in range(_LOAD_DATA_THRESHOLD)]
        dialect = MySQLDialect()
        with engine_no_infile.begin() as conn:
            with pytest.raises(RuntimeError, match="local_infile"):
                dialect.bulk_insert(conn, table, records, bulk_load=True)
    finally:
        _drop(meta, engine_no_infile)
        engine_no_infile.dispose()
