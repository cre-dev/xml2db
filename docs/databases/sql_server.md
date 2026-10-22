---
title: "Load XML into SQL Server"
description: "Load complex XML files into Microsoft SQL Server tables generated from an XSD schema with xml2db: pyodbc connection, bcp bulk loading, columnstore indexes and type mapping."
---

# Load XML into SQL Server

`xml2db` creates SQL Server tables from an XSD schema and loads XML files into them, using the `bcp` utility for bulk
loading when it is installed.

## Connecting

Install `pyodbc` and a Microsoft ODBC driver (for example ODBC Driver 18 for SQL Server), then pass a SQLAlchemy
connection string:

``` bash
pip install xml2db pyodbc

xml2db import file.xml schema.xsd \
    --connection-string "mssql+pyodbc://user:pw@host:1433/db?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes" \
    --db-schema xml_data
```

``` py title="Python API" linenums="1"
from xml2db import DataModel

data_model = DataModel(
    xsd_file="schema.xsd",
    connection_string="mssql+pyodbc://user:pw@host:1433/db?driver=ODBC+Driver+18+for+SQL+Server",
    db_schema="xml_data",
)
data_model.parse_xml("file.xml").insert_into_target_tables()
```

When `DataModel` creates the engine from a connection string, it enables `fast_executemany` and uses the
`SERIALIZABLE` isolation level. If you pass your own engine with `db_engine`, set these options yourself:

``` py
import sqlalchemy

engine = sqlalchemy.create_engine(
    connection_string, fast_executemany=True, isolation_level="SERIALIZABLE"
)
data_model = DataModel(xsd_file="schema.xsd", db_engine=engine)
```

## Bulk loading

Batches of 100 rows or more are loaded into staging tables with `bcp` when these conditions are met:

* the `bcp` executable is on the `PATH` (package `mssql-tools18` on Linux and macOS, SQL Server Command Line
  Utilities on Windows);
* the connection uses SQL Server authentication (user and password in the connection string) or a trusted connection
  (`Trusted_Connection=yes`).

`TrustServerCertificate=yes` in the connection string is passed on to `bcp`. Smaller batches, or any batch when these
conditions are not met, use `fast_executemany`.

`bcp` runs as a separate process, outside the SQLAlchemy transaction. This only concerns staging tables: the merge
into target tables still runs in a transaction. Tab characters inside values are replaced by spaces on this path; pass
`bulk_load=False` to `insert_into_target_tables` if they must be kept.

## Columnstore indexes

For large analytical tables, `xml2db` can create a clustered columnstore index on selected tables. The primary key
of these tables then becomes nonclustered.

``` yaml title="model_config.yml"
tables:
  TimeSeries:
    as_columnstore: true
```

Relationship tables between deduplicated tables have no primary key: they get a clustered index on their two foreign
keys.

## Column types

| XSD type | SQL Server type |
|---|---|
| `string` without `maxLength` | `VARCHAR(1000)` |
| `string` with `maxLength` | `VARCHAR(n)`, or `CHAR(n)` when the length is fixed |
| `decimal`, `float`, `double` | `DOUBLE PRECISION` (`FLOAT(53)`) |
| `dateTime` | `DATETIMEOFFSET` |
| `date`, `time` | `VARCHAR` (XSD values may carry a time zone) |
| Repeated simple values joined in one column | `VARCHAR(8000)` |
| Other types, such as `anyURI` | `VARCHAR(1000)`, with a warning |

The `xml2db_record_hash` column used for deduplication is `BINARY(20)` with the default hash function.

Text columns are `VARCHAR`. To store characters outside the code page of your database collation, use a UTF-8
collation (SQL Server 2019 and later), or override column types with `NVARCHAR` in a Python configuration:

``` py
from sqlalchemy.dialects.mssql import NVARCHAR

model_config = {
    "tables": {"invoice": {"fields": {"customer_name": {"type": NVARCHAR(200)}}}}
}
```

SQL Server accepts identifiers up to 128 characters, so table and column names are not shortened.

## Concurrent loads

Each `DataModel` instance uses its own staging tables (named with a random `temp_prefix`), so several processes can
fill staging tables at the same time. The merge into target tables should run one process at a time: see
[Multiprocessing](../how_it_works.md#multiprocessing) for an example.
