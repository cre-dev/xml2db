---
title: "Load XML into SQLite, Parquet or Delta Lake"
description: "Use xml2db with DuckDB as a staging database to load complex XML files into SQLite, Parquet files, Delta Lake, DuckLake or Iceberg tables, with full or incremental copies."
---

# Load XML into SQLite, Parquet or Delta Lake

`xml2db` merges each file into existing tables: it matches records by hash, generates keys and links rows through
foreign keys. This needs a database with sequences or identity columns, unique constraints and `UPDATE` statements. Files
and table formats such as Parquet or Delta Lake do not offer this, and SQLite is not supported.

[DuckDB](duckdb.md) fills the gap. Load the XML files into a DuckDB file, which keeps the state needed for
deduplication, then copy its tables to the target with a DuckDB extension:

| Target | DuckDB extension | Copy method |
|---|---|---|
| SQLite | `sqlite` | `ATTACH ... (TYPE sqlite)`, then `CREATE TABLE ... AS` |
| Parquet files | built in | `COPY ... TO ... (FORMAT parquet)` |
| DuckLake | `ducklake` | `ATTACH 'ducklake:...'`, then `CREATE TABLE ... AS` |
| Delta Lake | `delta` | `ATTACH ... (TYPE delta)`, then `CREATE TABLE` and `INSERT` |
| Iceberg | `iceberg` | Through an Iceberg REST catalog, see the [DuckDB documentation](https://duckdb.org/docs/current/core_extensions/iceberg/overview) |

The examples below were tested with DuckDB 2.0 and local files. Extensions are downloaded on first use.

!!! note
    Pointing `xml2db` directly at a database attached in DuckDB does not work: DuckDB cannot create the sequences
    used for primary keys in attached PostgreSQL or SQLite databases.

## Load into a staging DuckDB file

``` py title="load.py" linenums="1"
from xml2db import DataModel

data_model = DataModel(xsd_file="schema.xsd", connection_string="duckdb:///staging.duckdb")
for xml_file in xml_files:
    data_model.parse_xml(xml_file).insert_into_target_tables()
data_model.engine.dispose()
```

Keep `staging.duckdb` between runs: it holds the hashes used to store each record once. Starting from an empty file
restarts deduplication and key numbering.

## Copy all tables

The function below lists the tables of the staging file and copies them to an attached database, replacing previous
copies. Run it once loading is finished, from a single process.

``` py title="copy_all.py" linenums="1"
import duckdb


def staging_tables(con):
    """List the tables xml2db created in the staging DuckDB file."""
    return [
        row[0]
        for row in con.execute(
            "SELECT table_name FROM duckdb_tables() "
            "WHERE database_name = current_database() AND schema_name = 'main'"
        ).fetchall()
    ]


def copy_all(con, target):
    """Copy every table to an attached database, replacing previous copies."""
    for table in staging_tables(con):
        con.execute(f'CREATE OR REPLACE TABLE {target}."{table}" AS FROM "{table}"')


con = duckdb.connect("staging.duckdb")
con.execute("ATTACH 'xml_data.sqlite' AS target (TYPE sqlite)")
copy_all(con, "target")
```

The same function writes to DuckLake, with `ATTACH 'ducklake:xml_data.ducklake' AS target (DATA_PATH 'files/')`.

For Parquet, write one file per table:

``` py
for table in staging_tables(con):
    con.execute(f"COPY \"{table}\" TO 'parquet/{table}.parquet' (FORMAT parquet)")
```

Copies made with `CREATE TABLE ... AS` keep columns and their types, as far as the target supports them, but not
primary keys, foreign keys or unique constraints.

## Copy new rows only

`xml2db` never updates or deletes rows of the target tables: loading a file only appends rows. Keys come from
sequences, so new rows have higher primary keys than existing ones. Relationship tables have no primary key, but a new
row always points to a new parent row, and the parent key is their first column.

This gives a simple incremental copy: for each table, append the rows whose first column is greater than its highest
value in the target.

``` py title="copy_new_rows.py" linenums="1"
def copy_new_rows(con, target):
    """Append the rows added since the previous copy to an attached database."""
    existing = {
        row[0]
        for row in con.execute(
            "SELECT table_name FROM duckdb_tables() WHERE database_name = ?", [target]
        ).fetchall()
    }
    for table in staging_tables(con):
        if table not in existing:
            con.execute(f'CREATE TABLE {target}."{table}" AS FROM "{table}"')
            continue
        # first column: the primary key, or the parent key of a relationship table
        key = con.execute(
            "SELECT column_name FROM duckdb_columns() WHERE database_name = current_database() "
            "AND table_name = ? ORDER BY column_index LIMIT 1",
            [table],
        ).fetchone()[0]
        con.execute(
            f'INSERT INTO {target}."{table}" FROM "{table}" '
            f'WHERE "{key}" > (SELECT coalesce(max("{key}"), 0) FROM {target}."{table}")'
        )
```

## Delta Lake

A Delta table is attached on its own, and DuckDB does not support `CREATE TABLE ... AS` for Delta. Create each table
from the staging column types, then append new rows as above:

``` py title="copy_to_delta.py" linenums="1"
def copy_new_rows_to_delta(con, root):
    """Append new rows to one Delta table per staging table, under the root path."""
    for table in staging_tables(con):
        con.execute(f"ATTACH '{root}/{table}' AS delta_target (TYPE delta)")
        columns = con.execute(
            "SELECT column_name, data_type FROM duckdb_columns() "
            "WHERE database_name = current_database() AND table_name = ? ORDER BY column_index",
            [table],
        ).fetchall()
        if not con.execute(
            "SELECT count(*) FROM duckdb_tables() WHERE database_name = 'delta_target'"
        ).fetchone()[0]:
            definition = ", ".join(f'"{name}" {data_type}' for name, data_type in columns)
            con.execute(f"CREATE TABLE delta_target.delta_target ({definition})")
        key = columns[0][0]
        con.execute(
            f'INSERT INTO delta_target FROM "{table}" '
            f'WHERE "{key}" > (SELECT coalesce(max("{key}"), 0) FROM delta_target)'
        )
        con.execute("DETACH delta_target")


con = duckdb.connect("staging.duckdb")
copy_new_rows_to_delta(con, "s3://bucket/xml_data")  # or a local directory
```

Delta write support depends on the DuckDB version and platform: check the
[delta extension documentation](https://duckdb.org/docs/current/core_extensions/delta) for current limitations.
Writing to object storage also needs credentials, set up with DuckDB secrets.
