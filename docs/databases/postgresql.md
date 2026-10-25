---
title: "Load XML into PostgreSQL"
description: "Load complex XML files into PostgreSQL tables generated from an XSD with xml2db: drivers, COPY bulk loading, names, types and concurrent loads."
---

# Load XML into PostgreSQL

`xml2db` creates PostgreSQL tables from an XSD schema and loads XML files into them, using `COPY` for bulk loading.

## Connecting

Install a driver alongside `xml2db`:

``` bash
pip install xml2db psycopg2-binary   # or: pip install xml2db "psycopg[binary]"
```

Then pass a SQLAlchemy connection string:

``` bash
xml2db import file.xml schema.xsd \
    --connection-string "postgresql+psycopg2://user:pw@host:5432/db" \
    --db-schema xml_data
```

``` py title="Python API" linenums="1"
from xml2db import DataModel

data_model = DataModel(
    xsd_file="schema.xsd",
    connection_string="postgresql+psycopg://user:pw@host:5432/db",
    db_schema="xml_data",
)
data_model.parse_xml("file.xml").insert_into_target_tables()
```

The schema given with `--db-schema` or `db_schema` is created if it does not exist. Without it, tables go to the
default schema of the connection, usually `public`.

## Bulk loading

With `psycopg2` or `psycopg` (version 3), staging tables are filled with `COPY ... FROM STDIN`: rows are written to an
in-memory CSV buffer and streamed to the server, with no temporary file. `COPY` is used for every batch, whatever its
size. Other drivers, such as `pg8000`, fall back to standard `executemany` inserts.

`insert_into_target_tables(bulk_load=True)` raises an error when the driver does not support
`COPY`. See [Bulk loading](../how_it_works.md#bulk-loading) for the other options.

## Table and column names

PostgreSQL truncates identifiers longer than 63 characters. `xml2db` shortens such names itself, keeping the first
characters and adding a 7-character hash suffix, so names stay unique and stable between runs. Deep XSD hierarchies
often produce long names: rename them in the configuration to keep them readable.

``` yaml title="model_config.yml"
tables:
  TimeSeries:
    fields:
      production_RegisteredResource_pSRType_powerSystemResources_nominalP:
        rename: nominal_power
```

`xml2db render schema.xsd --format ddl --db-type postgresql` shows the physical names before anything is created.

## Column types

The default mapping favours loading every file without errors over precise types:

| XSD type | PostgreSQL type |
|---|---|
| `string` without `maxLength` | `VARCHAR(1000)` |
| `string` with `maxLength` | `VARCHAR(n)` |
| `decimal`, `float`, `double` | `DOUBLE PRECISION` |
| `integer`, `int` and derived types | `INTEGER` |
| `long` | `BIGINT` |
| `boolean` | `BOOLEAN` |
| `dateTime` | `TIMESTAMP WITH TIME ZONE` |
| `date`, `time` | `VARCHAR` (XSD values may carry a time zone) |
| Repeated simple values joined in one column | `VARCHAR(8000)` |
| Other types, such as `anyURI` | `VARCHAR(1000)`, with a warning |

The `xml2db_record_hash` column used for deduplication is `BYTEA`.

Override a type when the default does not fit, for instance to keep exact decimal values for amounts:

``` yaml title="model_config.yml"
tables:
  line:
    fields:
      price:
        type: Numeric(12, 2)
      description:
        type: Text
```

## Concurrent loads

Each `DataModel` instance uses its own staging tables (named with a random `temp_prefix`), so several processes can
fill staging tables at the same time. The merge into target tables should run one process at a time: see
[Multiprocessing](../how_it_works.md#multiprocessing) for an example.
