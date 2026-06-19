"""Integration tests for PostgreSQLDialect.bulk_insert with psycopg2 and psycopg3."""
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

from xml2db.dialect.postgresql import PostgreSQLDialect


def _make_pg_engine(driver: str):
    """Return a PostgreSQL engine using the given driver, or skip."""
    db_string = os.getenv("DB_STRING", "")
    if not db_string:
        pytest.skip("DB_STRING not set")
    url = make_url(db_string)
    if url.get_dialect().name != "postgresql":
        pytest.skip("DB_STRING is not a PostgreSQL connection")
    if driver == "psycopg2":
        pytest.importorskip("psycopg2")
    else:
        pytest.importorskip("psycopg")
    url = url.set(drivername=f"postgresql+{driver}")
    return create_engine(url)


@pytest.fixture(params=["psycopg2", "psycopg"])
def pg_engine(request):
    engine = _make_pg_engine(request.param)
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


def _roundtrip(engine, table, records):
    dialect = PostgreSQLDialect()
    with engine.begin() as conn:
        dialect.bulk_insert(conn, table, records)
    with engine.connect() as conn:
        return conn.execute(select(table).order_by(table.c.id)).mappings().all()


def _drop(meta, engine):
    meta.drop_all(engine)


# ---------------------------------------------------------------------------
# Basic types
# ---------------------------------------------------------------------------


@pytest.mark.dbtest
def test_pg_bulk_insert_basic(pg_engine):
    table, meta = _make_table(pg_engine, "pg_bi_basic")
    try:
        records = [{"id": 1, "label": "hello"}, {"id": 2, "label": None}]
        rows = _roundtrip(pg_engine, table, records)
        assert len(rows) == 2
        assert rows[0]["id"] == 1
        assert rows[0]["label"] == "hello"
        assert rows[1]["label"] is None
    finally:
        _drop(meta, pg_engine)


@pytest.mark.dbtest
def test_pg_bulk_insert_empty(pg_engine):
    table, meta = _make_table(pg_engine, "pg_bi_empty")
    try:
        dialect = PostgreSQLDialect()
        with pg_engine.begin() as conn:
            dialect.bulk_insert(conn, table, [])
        with pg_engine.connect() as conn:
            count = conn.execute(select(table)).rowcount
        assert count == 0
    finally:
        _drop(meta, pg_engine)


# ---------------------------------------------------------------------------
# Numeric types
# ---------------------------------------------------------------------------


@pytest.mark.dbtest
def test_pg_bulk_insert_numeric_types(pg_engine):
    meta = MetaData()
    table = Table(
        "pg_bi_numeric",
        meta,
        Column("i", Integer, key="i"),
        Column("bi", BigInteger, key="bi"),
        Column("si", SmallInteger, key="si"),
        Column("d", Double, key="d"),
    )
    meta.create_all(pg_engine)
    try:
        records = [{"i": 1, "bi": 10**15, "si": 32767, "d": 3.14}]
        dialect = PostgreSQLDialect()
        with pg_engine.begin() as conn:
            dialect.bulk_insert(conn, table, records)
        with pg_engine.connect() as conn:
            rows = conn.execute(select(table)).mappings().all()
        assert rows[0]["i"] == 1
        assert rows[0]["bi"] == 10**15
        assert rows[0]["si"] == 32767
        assert abs(rows[0]["d"] - 3.14) < 1e-9
    finally:
        meta.drop_all(pg_engine)


# ---------------------------------------------------------------------------
# Boolean
# ---------------------------------------------------------------------------


@pytest.mark.dbtest
def test_pg_bulk_insert_boolean(pg_engine):
    meta = MetaData()
    table = Table(
        "pg_bi_bool",
        meta,
        Column("id", Integer, key="id"),
        Column("flag", Boolean, key="flag"),
    )
    meta.create_all(pg_engine)
    try:
        records = [
            {"id": 1, "flag": True},
            {"id": 2, "flag": False},
            {"id": 3, "flag": None},
        ]
        dialect = PostgreSQLDialect()
        with pg_engine.begin() as conn:
            dialect.bulk_insert(conn, table, records)
        with pg_engine.connect() as conn:
            rows = conn.execute(select(table).order_by(table.c.id)).mappings().all()
        assert rows[0]["flag"] is True
        assert rows[1]["flag"] is False
        assert rows[2]["flag"] is None
    finally:
        meta.drop_all(pg_engine)


# ---------------------------------------------------------------------------
# DateTime
# ---------------------------------------------------------------------------


@pytest.mark.dbtest
def test_pg_bulk_insert_datetime(pg_engine):
    meta = MetaData()
    table = Table(
        "pg_bi_dt",
        meta,
        Column("id", Integer, key="id"),
        Column("ts", DateTime(timezone=True), key="ts"),
    )
    meta.create_all(pg_engine)
    try:
        dt = datetime.datetime(2023, 9, 27, 14, 35, 54, 274602,
                               tzinfo=datetime.timezone.utc)
        records = [{"id": 1, "ts": dt}, {"id": 2, "ts": None}]
        dialect = PostgreSQLDialect()
        with pg_engine.begin() as conn:
            dialect.bulk_insert(conn, table, records)
        with pg_engine.connect() as conn:
            rows = conn.execute(select(table).order_by(table.c.id)).mappings().all()
        assert rows[0]["ts"] is not None
        assert rows[1]["ts"] is None
    finally:
        meta.drop_all(pg_engine)


# ---------------------------------------------------------------------------
# Binary (bytea)
# ---------------------------------------------------------------------------


@pytest.mark.dbtest
def test_pg_bulk_insert_binary(pg_engine):
    meta = MetaData()
    table = Table(
        "pg_bi_binary",
        meta,
        Column("id", Integer, key="id"),
        Column("data", LargeBinary, key="data"),
    )
    meta.create_all(pg_engine)
    try:
        payload = b"\xde\xad\xbe\xef" * 8
        records = [{"id": 1, "data": payload}, {"id": 2, "data": None}]
        dialect = PostgreSQLDialect()
        with pg_engine.begin() as conn:
            dialect.bulk_insert(conn, table, records)
        with pg_engine.connect() as conn:
            rows = conn.execute(select(table).order_by(table.c.id)).mappings().all()
        assert bytes(rows[0]["data"]) == payload
        assert rows[1]["data"] is None
    finally:
        meta.drop_all(pg_engine)


# ---------------------------------------------------------------------------
# Python-side scalar column defaults
# ---------------------------------------------------------------------------


@pytest.mark.dbtest
def test_pg_bulk_insert_scalar_column_default(pg_engine):
    meta = MetaData()
    table = Table(
        "pg_bi_default",
        meta,
        Column("id", Integer, key="id"),
        Column("flag", Boolean, default=False, key="flag"),
    )
    meta.create_all(pg_engine)
    try:
        # Records do NOT contain 'flag'; the default must be applied.
        records = [{"id": 1}, {"id": 2}]
        dialect = PostgreSQLDialect()
        with pg_engine.begin() as conn:
            dialect.bulk_insert(conn, table, records)
        with pg_engine.connect() as conn:
            rows = conn.execute(select(table).order_by(table.c.id)).mappings().all()
        assert rows[0]["flag"] is False
        assert rows[1]["flag"] is False
    finally:
        meta.drop_all(pg_engine)
