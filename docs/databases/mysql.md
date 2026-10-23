---
title: "Load XML into MySQL and MariaDB"
description: "Load complex XML files into MySQL or MariaDB tables generated from an XSD schema with xml2db: drivers, LOAD DATA LOCAL INFILE bulk loading, identifier limits and string sizes."
---

# Load XML into MySQL and MariaDB

`xml2db` creates MySQL tables from an XSD schema and loads XML files into them, using `LOAD DATA LOCAL INFILE` for
bulk loading. MariaDB uses the same code path; integration tests run against MySQL only.

## Connecting

Install `pymysql` or `mysqlclient`, then pass a SQLAlchemy connection string:

``` bash
pip install xml2db pymysql

xml2db import file.xml schema.xsd \
    --connection-string "mysql+pymysql://user:pw@host:3306/db" \
    --db-schema xml_data
```

``` py title="Python API" linenums="1"
from xml2db import DataModel

data_model = DataModel(
    xsd_file="schema.xsd",
    connection_string="mysql+pymysql://user:pw@host:3306/db",
    db_schema="xml_data",
)
data_model.parse_xml("file.xml").insert_into_target_tables()
```

In MySQL, a schema is a database: `--db-schema xml_data` creates the `xml_data` database if it does not exist. Use
`mariadb+pymysql://` for MariaDB.

## Bulk loading

With `pymysql` or `mysqlclient`, batches of 100 rows or more are written to a temporary tab-separated file and sent
with `LOAD DATA LOCAL INFILE`. Two settings are needed:

* on the client, `local_infile=True` in the connection arguments. `DataModel` adds it when it creates the engine from a
  connection string. If you pass your own engine, add it yourself:
  `sqlalchemy.create_engine(url, connect_args={"local_infile": True})`;
* on the server, `local_infile=ON`, for instance by starting it with `--local-infile=1`. Check with
  `SHOW VARIABLES LIKE 'local_infile'`.

When the server refuses `LOAD DATA LOCAL INFILE`, `xml2db` falls back to `executemany` and keeps doing so for the
following batches of the same `DataModel`.
`insert_into_target_tables(bulk_load=True)` raises an error instead, which helps to check the setup.

## String sizes

Strings without a `maxLength` in the XSD become `VARCHAR(255)` on MySQL, while other backends use
`VARCHAR(1000)`. Longer values are rejected in strict SQL mode, which is the default. Override the type of free-text fields:

``` yaml title="model_config.yml"
tables:
  line:
    fields:
      description:
        type: Text
```

MySQL also limits the total size of a row to 65,535 bytes, counting each `VARCHAR` column at its maximum size. Tables
with many string columns can reach this limit, especially with `utf8mb4` (4 bytes per character). `Text` columns only
count for a few bytes each, so the same override solves the "Row size too large" error.

Repeated simple values joined in one column use `VARCHAR(4000)`.

## Table and column names

MySQL accepts identifiers up to 64 characters. `xml2db` shortens names longer than 56 characters, keeping room for the
suffixes SQLAlchemy adds to constraint names. Shortened names keep their first characters and get a 7-character hash
suffix, so they stay unique and stable between runs. Use `rename` in the configuration to choose readable names, and
`xml2db render schema.xsd --format ddl --db-type mysql` to see the result.

## Concurrent loads

Each `DataModel` instance uses its own staging tables (named with a random `temp_prefix`), so several processes can
fill staging tables at the same time. The merge into target tables should run one process at a time: see
[Multiprocessing](../how_it_works.md#multiprocessing) for an example.
