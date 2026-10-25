---
title: "Load XML into DuckDB"
description: "Load complex XML files into DuckDB tables generated from an XSD with xml2db, query them without a server, or read simple XML with DuckDB extensions."
---

# Load XML into DuckDB

DuckDB runs inside the Python process and stores a whole database in a single file. With `xml2db`, it gives a
relational copy of XML files without any server to set up, which suits local analysis, trying a data model before
deploying it, and tests.

## Reading XML in DuckDB

DuckDB community extensions, such as [webbed](https://duckdb.org/community_extensions/extensions/webbed), add a
`read_xml` function that reads XML files directly in SQL. It turns a repeated element into rows, with nested elements
as `STRUCT` and `LIST` columns, and needs no XSD. It fits quick queries on record-like files.

`xml2db` fits files described by an XSD, with deep nesting or repeated elements at several levels: it loads them into
normalized tables with keys, stores identical records once, and gives the same tables for every file of a feed. Both
work in the same DuckDB database, so each can be used where it fits.

## Connecting

``` bash
pip install xml2db duckdb-engine

xml2db import invoices.xml invoices.xsd --connection-string "duckdb:///invoices.duckdb"
```

``` py title="Python API" linenums="1"
from xml2db import DataModel

data_model = DataModel(
    xsd_file="invoices.xsd",
    connection_string="duckdb:///invoices.duckdb",
)
for xml_file in ["invoices_1.xml", "invoices_2.xml"]:
    data_model.parse_xml(xml_file).insert_into_target_tables()
```

Use `duckdb:///:memory:` for a database that only lives during the Python process.

Then query the file with the DuckDB command line or from Python:

``` py
import duckdb

con = duckdb.connect("invoices.duckdb", read_only=True)
con.sql("SELECT id, customer_name, CAST(date AS DATE) AS date FROM invoice").show()
```

XSD `date` and `time` values are stored as text, since they may carry a time zone: cast them in queries or views.

## Bulk loading

Batches of 100 rows or more are written to a temporary CSV file and loaded with DuckDB's `read_csv`, every column being
read as text and then cast to its target type. Smaller batches use `executemany`.

## One writer at a time

A DuckDB file accepts a single writing process. When loading files from several processes, parse in parallel and
load one file at a time, as shown in [Multiprocessing](../how_it_works.md#multiprocessing). Readers using
`read_only=True` cannot open the file while a process writes to it either.

## Keys and names

Primary keys are filled from DuckDB sequences, named `pk_sequ_<table>`. Table and column names longer than 63
characters are shortened with a hash suffix, as for PostgreSQL. This limit comes from the SQLAlchemy integration: DuckDB
itself accepts longer names.

## Transforming and exporting

Keep the DuckDB file as the raw copy of your XML data, and build the tables you need with SQL views or
[dbt](../dbt.md). DuckDB then exports them to Parquet files, Delta Lake, Iceberg and other targets that `xml2db` does
not support directly: see [Export to files, lakehouses and other databases](export.md).
