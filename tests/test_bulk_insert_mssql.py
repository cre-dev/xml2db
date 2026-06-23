"""Integration tests for MSSQLDialect.bulk_insert (fast_executemany and BCP)."""
import os

import pytest
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
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

from xml2db.dialect.mssql import MSSQLDialect, _BCP_THRESHOLD


def _make_mssql_engine():
    db_string = os.getenv("DB_STRING", "")
    if not db_string:
        pytest.skip("DB_STRING not set")
    url = make_url(db_string)
    if url.get_dialect().name != "mssql":
        pytest.skip("DB_STRING is not an MSSQL connection")
    pytest.importorskip("pyodbc")
    return create_engine(url, fast_executemany=True)


@pytest.fixture(scope="module")
def mssql_engine():
    engine = _make_mssql_engine()
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


def _insert_and_read(engine, table, records, **bulk_insert_kwargs):
    dialect = MSSQLDialect()
    with engine.begin() as conn:
        dialect.bulk_insert(conn, table, records, **bulk_insert_kwargs)
    with engine.connect() as conn:
        return conn.execute(select(table).order_by(table.c.id)).mappings().all()


def _drop(meta, engine):
    meta.drop_all(engine)


# ---------------------------------------------------------------------------
# fast_executemany path (< _BCP_THRESHOLD rows)
# ---------------------------------------------------------------------------


@pytest.mark.dbtest
def test_mssql_fast_executemany_basic(mssql_engine):
    table, meta = _make_table(mssql_engine, "mssql_bi_basic_fem")
    try:
        records = [{"id": 1, "label": "hello"}, {"id": 2, "label": None}]
        rows = _insert_and_read(mssql_engine, table, records)
        assert len(rows) == 2
        assert rows[0]["label"] == "hello"
        assert rows[1]["label"] is None
    finally:
        _drop(meta, mssql_engine)


@pytest.mark.dbtest
def test_mssql_fast_executemany_numeric(mssql_engine):
    meta = MetaData()
    table = Table(
        "mssql_bi_numeric_fem",
        meta,
        Column("id", Integer, key="id"),
        Column("i", Integer, key="i"),
        Column("bi", BigInteger, key="bi"),
        Column("si", SmallInteger, key="si"),
    )
    meta.create_all(mssql_engine)
    try:
        records = [{"id": 1, "i": 1, "bi": 10**15, "si": 32767}]
        rows = _insert_and_read(mssql_engine, table, records)
        assert rows[0]["i"] == 1
        assert rows[0]["bi"] == 10**15
        assert rows[0]["si"] == 32767
    finally:
        meta.drop_all(mssql_engine)


@pytest.mark.dbtest
def test_mssql_fast_executemany_boolean(mssql_engine):
    meta = MetaData()
    table = Table(
        "mssql_bi_bool_fem",
        meta,
        Column("id", Integer, key="id"),
        Column("flag", Boolean, key="flag"),
    )
    meta.create_all(mssql_engine)
    try:
        records = [{"id": 1, "flag": True}, {"id": 2, "flag": False}, {"id": 3, "flag": None}]
        rows = _insert_and_read(mssql_engine, table, records)
        assert rows[0]["flag"] is True
        assert rows[1]["flag"] is False
        assert rows[2]["flag"] is None
    finally:
        meta.drop_all(mssql_engine)


@pytest.mark.dbtest
def test_mssql_fast_executemany_scalar_default(mssql_engine):
    meta = MetaData()
    table = Table(
        "mssql_bi_default_fem",
        meta,
        Column("id", Integer, key="id"),
        Column("flag", Boolean, default=False, key="flag"),
    )
    meta.create_all(mssql_engine)
    try:
        records = [{"id": 1}, {"id": 2}]
        rows = _insert_and_read(mssql_engine, table, records)
        assert rows[0]["flag"] is False
        assert rows[1]["flag"] is False
    finally:
        meta.drop_all(mssql_engine)


# ---------------------------------------------------------------------------
# BCP path (>= _BCP_THRESHOLD rows)
# ---------------------------------------------------------------------------


def _require_bcp():
    import shutil
    if shutil.which("bcp") is None:
        pytest.skip("bcp not found on PATH")


@pytest.mark.dbtest
def test_mssql_bcp_basic(mssql_engine):
    _require_bcp()
    table, meta = _make_table(mssql_engine, "mssql_bi_basic_bcp")
    try:
        records = [{"id": i, "label": f"row{i}"} for i in range(_BCP_THRESHOLD)]
        records.append({"id": _BCP_THRESHOLD, "label": None})
        rows = _insert_and_read(mssql_engine, table, records)
        assert len(rows) == _BCP_THRESHOLD + 1
        assert rows[0]["label"] == "row0"
        assert rows[-1]["label"] is None
    finally:
        _drop(meta, mssql_engine)


@pytest.mark.dbtest
def test_mssql_bcp_numeric(mssql_engine):
    _require_bcp()
    meta = MetaData()
    table = Table(
        "mssql_bi_numeric_bcp",
        meta,
        Column("i", Integer, key="i"),
        Column("bi", BigInteger, key="bi"),
        Column("si", SmallInteger, key="si"),
    )
    meta.create_all(mssql_engine)
    try:
        base = [{"i": j, "bi": 10**15 + j, "si": j % 32767} for j in range(_BCP_THRESHOLD)]
        dialect = MSSQLDialect()
        with mssql_engine.begin() as conn:
            dialect.bulk_insert(conn, table, base)
        with mssql_engine.connect() as conn:
            rows = conn.execute(select(table).order_by(table.c.i)).mappings().all()
        assert rows[0]["bi"] == 10**15
    finally:
        meta.drop_all(mssql_engine)


@pytest.mark.dbtest
def test_mssql_bcp_boolean(mssql_engine):
    _require_bcp()
    meta = MetaData()
    table = Table(
        "mssql_bi_bool_bcp",
        meta,
        Column("id", Integer, key="id"),
        Column("flag", Boolean, key="flag"),
    )
    meta.create_all(mssql_engine)
    try:
        records = (
            [{"id": 0, "flag": True}, {"id": 1, "flag": False}, {"id": 2, "flag": None}]
            + [{"id": i + 3, "flag": i % 2 == 0} for i in range(_BCP_THRESHOLD)]
        )
        dialect = MSSQLDialect()
        with mssql_engine.begin() as conn:
            dialect.bulk_insert(conn, table, records)
        with mssql_engine.connect() as conn:
            rows = conn.execute(select(table).order_by(table.c.id)).mappings().all()
        assert rows[0]["flag"] is True
        assert rows[1]["flag"] is False
        assert rows[2]["flag"] is None
    finally:
        meta.drop_all(mssql_engine)


@pytest.mark.dbtest
def test_mssql_bcp_binary(mssql_engine):
    _require_bcp()
    meta = MetaData()
    table = Table(
        "mssql_bi_binary_bcp",
        meta,
        Column("id", Integer, key="id"),
        Column("data", LargeBinary, key="data"),
    )
    meta.create_all(mssql_engine)
    try:
        payload = b"\xde\xad\xbe\xef" * 8
        records = (
            [{"id": 0, "data": payload}, {"id": 1, "data": None}]
            + [{"id": i + 2, "data": payload} for i in range(_BCP_THRESHOLD)]
        )
        dialect = MSSQLDialect()
        with mssql_engine.begin() as conn:
            dialect.bulk_insert(conn, table, records)
        with mssql_engine.connect() as conn:
            rows = conn.execute(select(table).order_by(table.c.id)).mappings().all()
        assert bytes(rows[0]["data"]) == payload
        assert rows[1]["data"] is None
    finally:
        meta.drop_all(mssql_engine)


@pytest.mark.dbtest
def test_mssql_bcp_scalar_default(mssql_engine):
    _require_bcp()
    meta = MetaData()
    table = Table(
        "mssql_bi_default_bcp",
        meta,
        Column("id", Integer, key="id"),
        Column("flag", Boolean, default=False, key="flag"),
    )
    meta.create_all(mssql_engine)
    try:
        records = [{"id": i} for i in range(_BCP_THRESHOLD)]
        dialect = MSSQLDialect()
        with mssql_engine.begin() as conn:
            dialect.bulk_insert(conn, table, records)
        with mssql_engine.connect() as conn:
            rows = conn.execute(select(table).order_by(table.c.id)).mappings().all()
        assert all(r["flag"] is False for r in rows)
    finally:
        meta.drop_all(mssql_engine)


# ---------------------------------------------------------------------------
# bulk_load=False forces fast_executemany even for large batches
# ---------------------------------------------------------------------------


@pytest.mark.dbtest
def test_mssql_bulk_load_false_bypasses_bcp(mssql_engine):
    """bulk_load=False must use fast_executemany regardless of batch size."""
    table, meta = _make_table(mssql_engine, "mssql_bi_bulk_load_false")
    try:
        records = [{"id": i, "label": f"r{i}"} for i in range(_BCP_THRESHOLD)]
        rows = _insert_and_read(mssql_engine, table, records, bulk_load=False)
        assert len(rows) == _BCP_THRESHOLD
    finally:
        _drop(meta, mssql_engine)


# ---------------------------------------------------------------------------
# bulk_load=True raises when BCP is unavailable
# ---------------------------------------------------------------------------


@pytest.mark.dbtest
def test_mssql_bulk_load_true_raises_without_bcp(mssql_engine):
    """bulk_load=True must raise RuntimeError when bcp is not on PATH."""
    import shutil
    import unittest.mock as mock

    if shutil.which("bcp") is None:
        # BCP already absent; just confirm the error is raised directly.
        table, meta = _make_table(mssql_engine, "mssql_bi_bulk_load_true_no_bcp")
        try:
            records = [{"id": i, "label": f"r{i}"} for i in range(_BCP_THRESHOLD)]
            dialect = MSSQLDialect()
            with mssql_engine.begin() as conn:
                with pytest.raises(RuntimeError, match="bcp utility"):
                    dialect.bulk_insert(conn, table, records, bulk_load=True)
        finally:
            _drop(meta, mssql_engine)
    else:
        # BCP present; patch shutil.which to simulate absence.
        table, meta = _make_table(mssql_engine, "mssql_bi_bulk_load_true_no_bcp")
        try:
            records = [{"id": i, "label": f"r{i}"} for i in range(_BCP_THRESHOLD)]
            dialect = MSSQLDialect()
            with mock.patch("xml2db.dialect.mssql.shutil.which", return_value=None):
                with mssql_engine.begin() as conn:
                    with pytest.raises(RuntimeError, match="bcp utility"):
                        dialect.bulk_insert(conn, table, records, bulk_load=True)
        finally:
            _drop(meta, mssql_engine)
