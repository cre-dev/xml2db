---
title: "Load XML into SQLite, Parquet or Delta Lake"
description: "Use xml2db with DuckDB to keep all the data of complex XML files, transform it with SQL, and export the resulting tables to Parquet files, SQLite, DuckLake, Delta Lake or Iceberg."
---

# Load XML into SQLite, Parquet or Delta Lake

`xml2db` merges each file into existing tables: it matches records by hash, generates keys and links rows through
foreign keys. This needs a database with sequences or identity columns, unique constraints and `UPDATE` statements.
Files and table formats such as Parquet or Delta Lake do not offer this, and SQLite is not supported.

[DuckDB](duckdb.md) fills the gap, and fits the [ELT approach](../index.md#load-first-transform-later):

1. load all the XML data into a DuckDB file, which keeps every element and the state needed for deduplication;
2. explore it, then join, filter and flatten it with SQL into the tables you need;
3. export these tables to the target with a DuckDB extension.

When the transformation changes, rerun steps 2 and 3 from the DuckDB file, without parsing the XML files again.

The examples below use the invoices schema of the [introduction](../index.md#from-xml-to-tables). They were tested
with DuckDB 2.0 and local files. Extensions are downloaded on first use.

## Load everything into DuckDB

``` py title="load.py" linenums="1"
from xml2db import DataModel

data_model = DataModel(xsd_file="invoices.xsd", connection_string="duckdb:///invoices.duckdb")
for xml_file in xml_files:
    data_model.parse_xml(xml_file).insert_into_target_tables()
data_model.engine.dispose()
```

Keep `invoices.duckdb` between runs: it holds all the source data, and the hashes used to store each record once.

## Transform with SQL

Build the tables your users need from the xml2db tables, for instance one row per invoice line, with proper types:

``` py title="transform.py" linenums="1"
import duckdb

con = duckdb.connect("invoices.duckdb")
con.execute("""
    CREATE OR REPLACE VIEW invoice_lines AS
    SELECT
        i.pk_invoice,
        i.id AS invoice_id,
        CAST(i.date AS DATE) AS invoice_date,
        i.customer_name,
        i.customer_country,
        l.sku,
        l.quantity,
        CAST(l.price AS DECIMAL(12, 2)) AS price
    FROM invoice AS i
    JOIN invoice_line AS il ON il.fk_invoice = i.pk_invoice
    JOIN line AS l ON l.pk_line = il.fk_line
""")
```

For more than a few views, [dbt](../dbt.md) organizes these transformations, tests them and makes them incremental.

## Export

| Target | DuckDB extension | Export |
|---|---|---|
| Parquet files | built in | `COPY invoice_lines TO 'invoice_lines.parquet' (FORMAT parquet)` |
| SQLite | `sqlite` | `ATTACH 'analytics.sqlite' AS lite (TYPE sqlite)`, then `CREATE OR REPLACE TABLE lite.invoice_lines AS FROM invoice_lines` |
| DuckLake | `ducklake` | `ATTACH 'ducklake:analytics.ducklake' AS lake (DATA_PATH 'files/')`, then `CREATE OR REPLACE TABLE lake.invoice_lines AS FROM invoice_lines` |
| Delta Lake | `delta` | `ATTACH ... (TYPE delta)`, then `CREATE TABLE` and `INSERT`, see below |
| Iceberg | `iceberg` | Through an Iceberg REST catalog, see the [DuckDB documentation](https://duckdb.org/docs/current/core_extensions/iceberg/overview) |

SQLite has no date or decimal types: DuckDB stores these columns as text there.

### Delta Lake and incremental exports

DuckDB does not support `CREATE TABLE ... AS` for Delta tables: create the table, then insert into it.

`xml2db` only appends rows to its tables, and new rows get higher keys. Filtering on the key of the table that defines
the grain of the export, `pk_invoice` here, appends new invoices only:

``` py title="export_delta.py" linenums="1"
con.execute("ATTACH 'delta/invoice_lines' AS delta_lines (TYPE delta)")
if not con.execute(
    "SELECT count(*) FROM duckdb_tables() WHERE database_name = 'delta_lines'"
).fetchone()[0]:
    con.execute("""
        CREATE TABLE delta_lines.delta_lines (
            pk_invoice INTEGER, invoice_id VARCHAR, invoice_date DATE, customer_name VARCHAR,
            customer_country VARCHAR, sku VARCHAR, quantity INTEGER, price DECIMAL(12, 2)
        )
    """)
con.execute("""
    INSERT INTO delta_lines
    FROM invoice_lines
    WHERE pk_invoice > (SELECT coalesce(max(pk_invoice), 0) FROM delta_lines)
""")
```

The same filter works for DuckLake, SQLite or any attached database with `INSERT INTO`. The
[dbt page](../dbt.md#incremental-models) explains how to choose the key.

Delta write support depends on the DuckDB version and platform: check the
[delta extension documentation](https://duckdb.org/docs/current/core_extensions/delta) for current limitations.
Writing to object storage also needs credentials, set up with DuckDB secrets.

## Copying the xml2db tables as they are

To give another tool the full relational copy, copy every table. Run it once loading is finished, from a single
process:

``` py title="copy_all.py" linenums="1"
import duckdb

con = duckdb.connect("invoices.duckdb")
con.execute("ATTACH 'invoices.sqlite' AS target (TYPE sqlite)")
tables = con.execute(
    "SELECT table_name FROM duckdb_tables() "
    "WHERE database_name = current_database() AND schema_name = 'main'"
).fetchall()
for (table,) in tables:
    con.execute(f'CREATE OR REPLACE TABLE target."{table}" AS FROM "{table}"')
```

Copies made with `CREATE TABLE ... AS` keep columns and their types, as far as the target supports them, but not
primary keys, foreign keys or unique constraints.

!!! note
    Pointing `xml2db` directly at a database attached in DuckDB does not work: DuckDB cannot create the sequences
    used for primary keys in attached PostgreSQL or SQLite databases.
