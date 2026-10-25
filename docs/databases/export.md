---
title: "Export to files, lakehouses and other databases"
description: "Load XML with xml2db into DuckDB, transform it with SQL, then export to Parquet, CSV or Excel, Delta Lake, Iceberg, warehouses or server databases."
---

# Export to files, lakehouses and other databases

`xml2db` merges each file into existing tables: it matches records by hash, generates keys and links rows through
foreign keys. This needs a database with sequences or identity columns, unique constraints and `UPDATE` statements,
which files and table formats such as Parquet or Delta Lake do not offer.

[DuckDB](duckdb.md) fills the gap, and fits the [ELT approach](../index.md#load-first-transform-later):

1. load all the XML data into a DuckDB file, which keeps every element and the state needed for deduplication;
2. explore it, then join, filter and flatten it with SQL into the tables you need;
3. export these tables with DuckDB.

When the transformation changes, rerun steps 2 and 3 from the DuckDB file: the XML files are parsed once.

The examples below use the invoices schema of the [introduction](../index.md#from-xml-to-tables). The examples
for single Parquet files, Delta Lake, DuckLake, PostgreSQL, DataFrames, CSV, JSON and Excel were tested with DuckDB 2.0
and local files. The examples for partitioned Parquet files, object storage, Iceberg and MySQL follow the DuckDB
documentation but were not tested with `xml2db`: they should work, check the linked pages for details.

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

Build the tables your users need from the `xml2db` tables, for instance one row per invoice line, with proper types:

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

## Parquet files

Parquet is read by most data tools: Spark, pandas, Polars, and the loaders of cloud data warehouses.

``` py
con.execute("COPY invoice_lines TO 'invoice_lines.parquet' (FORMAT parquet)")
```

Large tables can be split into one directory per value of a column, which should let tools reading the files skip
partitions:

``` py
con.execute("""
    COPY (SELECT *, year(invoice_date) AS invoice_year FROM invoice_lines)
    TO 'invoice_lines' (FORMAT parquet, PARTITION_BY (invoice_year))
""")
```

See [Parquet export](https://duckdb.org/docs/current/data/parquet/overview) and
[partitioned writes](https://duckdb.org/docs/current/data/partitioning/partitioned_writes) in the DuckDB
documentation.

### Object storage

With the `httpfs` extension and a secret holding the credentials, the same `COPY` statement should write directly to
S3 or S3-compatible storage:

``` py
con.execute("CREATE SECRET (TYPE s3, PROVIDER credential_chain)")
con.execute("COPY invoice_lines TO 's3://my-bucket/invoice_lines.parquet' (FORMAT parquet)")
```

The [S3 API page](https://duckdb.org/docs/current/core_extensions/httpfs/s3api) of the DuckDB documentation
describes the supported providers. For Azure Blob Storage or Google Cloud Storage, check the `azure` and `httpfs`
extension pages for write support.

### Cloud data warehouses

Cloud data warehouses load Parquet files from object storage with their own tools, such as `COPY INTO` statements or
external tables. Exporting Parquet files to a bucket, then loading them with these tools, should be the most reliable
path to a warehouse.

## Delta Lake

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

The [dbt page](../dbt.md#incremental-models) explains how to choose the key. Delta write support depends on the
DuckDB version and platform: check the [delta extension documentation](https://duckdb.org/docs/current/core_extensions/delta)
for current limitations.

## Iceberg

DuckDB writes Iceberg tables through an Iceberg REST catalog. Once the catalog is attached as described in the
[DuckDB documentation](https://duckdb.org/docs/current/core_extensions/iceberg/overview), `CREATE TABLE` and
`INSERT INTO` statements on the attached catalog should allow the same full or incremental exports as for Delta Lake.

## DuckLake

If your tools already rely on DuckDB, a [DuckLake](https://duckdb.org/docs/current/core_extensions/ducklake) catalog
gives a table format with snapshots on top of Parquet files:

``` py
con.execute("ATTACH 'ducklake:analytics.ducklake' AS lake (DATA_PATH 'files/')")
con.execute("CREATE OR REPLACE TABLE lake.invoice_lines AS FROM invoice_lines")
```

## Publishing to a server database

`xml2db` loads [PostgreSQL](postgresql.md) and [MySQL](mysql.md) directly. Another option is to keep the
`xml2db` tables in a local DuckDB file, and publish only the transformed tables to a shared server. The server
holds only the tables people query, and the parsing work stays on the machine running `xml2db`.

``` py
con.execute("ATTACH 'host=db.example.com dbname=analytics user=etl' AS pg (TYPE postgres)")
con.execute("CREATE OR REPLACE TABLE pg.public.invoice_lines AS FROM invoice_lines")
```

The `mysql` extension should allow the same with `ATTACH ... (TYPE mysql)`. Tables created this way have no primary
key, foreign keys or indexes: add them on the server if needed.

## DataFrames

To continue the analysis in Python, convert DuckDB results to pandas or Polars DataFrames:

``` py
invoice_lines = con.sql("FROM invoice_lines").df()  # pandas
invoice_lines = con.sql("FROM invoice_lines").pl()  # Polars
```

pandas converts `DECIMAL` columns to floating point numbers, while Polars keeps them as decimals.

## Other formats

DuckDB also writes CSV and JSON files, and `.xlsx` files with the `excel` extension, for small extracts (Excel sheets
hold about one million rows):

``` py
con.execute("COPY invoice_lines TO 'invoice_lines.csv'")
con.execute("COPY invoice_lines TO 'invoice_lines.json'")  # one JSON object per line

con.execute("INSTALL excel")
con.execute("LOAD excel")
con.execute("COPY invoice_lines TO 'invoice_lines.xlsx' (FORMAT xlsx, HEADER true)")
```

!!! note
    Pointing `xml2db` directly at a database attached in DuckDB does not work: DuckDB cannot create the sequences
    used for primary keys in attached databases such as PostgreSQL.
