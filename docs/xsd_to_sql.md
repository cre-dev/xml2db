---
title: "XSD to SQL tables"
description: "Generate SQL CREATE TABLE statements from an XSD schema with xml2db, for PostgreSQL, SQL Server or MySQL, and adjust the resulting relational schema with a configuration file."
---

# XSD to SQL tables

`xml2db` derives a relational schema from an XSD file. You can generate the `CREATE TABLE` statements without
connecting to a database or loading any XML file, to review the schema, share it, or create the tables with your own
deployment tools.

## From the command line

``` bash
xml2db render invoices.xsd --format ddl --db-type postgresql --output invoices.sql
```

`--db-type` accepts `postgresql`, `mssql`, `mysql` and `mariadb`. Without it, the statements use generic SQL.

For the invoices schema of the [introduction](index.md#from-xml-to-tables), this gives, among other tables:

``` sql
CREATE TABLE line (
	pk_line SERIAL NOT NULL,
	sku VARCHAR(1000),
	quantity INTEGER,
	price DOUBLE PRECISION,
	xml2db_record_hash BYTEA,
	CONSTRAINT cx_pk_line PRIMARY KEY (pk_line),
	CONSTRAINT line_xml2db_record_hash UNIQUE (xml2db_record_hash)
)

CREATE TABLE invoice (
	pk_invoice SERIAL NOT NULL,
	id VARCHAR(1000),
	date VARCHAR(16),
	customer_name VARCHAR(1000),
	customer_country VARCHAR(1000),
	xml2db_record_hash BYTEA,
	CONSTRAINT cx_pk_invoice PRIMARY KEY (pk_invoice),
	CONSTRAINT invoice_xml2db_record_hash UNIQUE (xml2db_record_hash)
)

CREATE TABLE invoice_line (
	fk_invoice INTEGER NOT NULL,
	fk_line INTEGER NOT NULL,
	FOREIGN KEY(fk_invoice) REFERENCES invoice (pk_invoice),
	FOREIGN KEY(fk_line) REFERENCES line (pk_line)
)
```

The same output is shown in the DDL tab of `xml2db serve`, next to the diagram, and updates as you edit the
configuration.

## How the schema is built

* Each complex type becomes a table, with an integer primary key named `pk_<table>`.
* Simple elements and attributes become columns, with types derived from the XSD types and their restrictions
  (`maxLength`, for instance).
* A child element that occurs at most once is merged into its parent as prefixed columns, such as `customer_name`.
* A repeated child element gets its own table. By default, identical records are stored once, identified by the
  `xml2db_record_hash` column, and a relationship table such as `invoice_line` links parents and children.

[How it works](how_it_works.md#building-a-data-model) describes these rules in detail.

## Adjusting the schema

The configuration file changes names, types and structure. For instance, this configuration renames a column, sets an
exact decimal type, and stores lines without deduplication, which replaces the `invoice_line` table with a foreign key
to the parent invoice:

``` yaml title="model_config.yml"
tables:
  invoice:
    fields:
      customer_name:
        rename: customer
  line:
    reuse: false
    fields:
      price:
        type: Numeric(12, 2)
```

``` bash
xml2db render invoices.xsd --format ddl --db-type postgresql --config model_config.yml
```

See [Configuring your data model](configuring.md) for all options, and the database pages for backend-specific
advice: [PostgreSQL](databases/postgresql.md), [SQL Server](databases/sql_server.md),
[MySQL and MariaDB](databases/mysql.md), [DuckDB](databases/duckdb.md).

## From Python

``` py title="Write the DDL to a file" linenums="1"
from sqlalchemy.dialects import postgresql
from xml2db import DataModel

data_model = DataModel(xsd_file="invoices.xsd", db_type="postgresql")
with open("invoices.sql", "w") as f:
    for statement in data_model.get_all_create_table_statements():
        f.write(f"{statement.compile(dialect=postgresql.dialect())};\n")
    for statement in data_model.get_all_create_index_statements():
        f.write(f"{statement.compile(dialect=postgresql.dialect())};\n")
```

When `xml2db` loads data, it creates missing tables itself: generating the DDL is not a required step.
