---
title: "Getting started"
description: "Step-by-step guide to installing xml2db, exploring an XSD schema with the CLI, importing XML into a relational database, and visualizing the resulting data model."
---

# Getting started

This guide walks you through installing xml2db, exploring and configuring a data model from an XSD schema, and loading XML files into a relational database.

## Installation

Install the package, preferably in a virtual environment:

``` bash
pip install xml2db
```

You will also need a database driver for your backend (e.g. `psycopg2` or `psycopg` for PostgreSQL, `pymysql` or `mysqlclient` for MySQL, `pyodbc` for SQL Server, `duckdb-engine` for DuckDB). See [How it works](how_it_works.md#bulk-loading) for which drivers enable native bulk loading.

!!! note
    To contribute to `xml2db` development, clone the repository and install in editable mode:

    ``` bash
    pip install -e .[docs,tests]
    ```

## Exploring the data model

The quickest way to understand your schema and configure the data model is the interactive browser explorer:

``` bash
xml2db serve path/to/schema.xsd
```

This opens a browser with four tabs:

- **ERD**: an entity-relationship diagram of the tables derived from the XSD
- **Target tree**: a text tree of the simplified data model that will be loaded into the database
- **Source tree**: a text tree of the raw XSD structure before simplification
- **DDL**: `CREATE TABLE` statements for the target schema

The left panel is a YAML config editor with autocomplete for table names, field names, and all config options. Edit the config and the diagram updates automatically. 
When the config looks right, click **Save** to write it to a file (default: `model_config.yml`).

You can also render these representations directly to stdout or a file without the browser:

``` bash
xml2db render schema.xsd --format erd
xml2db render schema.xsd --format target-tree
xml2db render schema.xsd --format source-tree
xml2db render schema.xsd --format ddl --db-type postgresql
```

See [Configuring your data model](configuring.md) for a full description of the available config options.

## Importing XML files

Once you are happy with the data model, import an XML file into the database (config is optional):

``` bash
xml2db import file.xml schema.xsd \
    --connection-string "postgresql+psycopg2://user:pw@host/db" \
    --config model_config.yml
```

On success, the command prints the number of rows inserted and already-existing (deduplicated), with per-phase timings.

Key options:

- `--config FILE`: YAML model config file
- `--db-schema SCHEMA`: target database schema
- `--metadata KEY=VALUE`: values for `metadata_columns` (e.g. `--metadata source=file.xml`)
- `--validate`: validate the XML against the schema before importing
- `--recover`: attempt to parse malformed XML

## Using the Python API

The same operations are available programmatically. Create a [`DataModel`](api/data_model.md) from an XSD file:

``` py title="Create a DataModel" linenums="1"
from xml2db import DataModel, load_config

data_model = DataModel(
    xsd_file="path/to/file.xsd",
    db_schema="source_data",
    connection_string="postgresql+psycopg2://user:pw@host/db",
    model_config=load_config("model_config.yml"),  # or a plain dict
)
```

A connection string is not required until you actually import data.

### Visualizing the data model

``` py title="Write an ERD to a file" linenums="1"
with open("data_model_erd.md", "w") as f:
    f.write(data_model.get_entity_rel_diagram())
```

The diagram uses [Mermaid](https://mermaid.js.org/syntax/entityRelationshipDiagram.html). Your IDE should be able to render Mermaid preview.

``` py title="Write source and target trees to files" linenums="1"
with open("source_tree.txt", "w") as f:
    f.write(data_model.source_tree)

with open("target_tree.txt", "w") as f:
    f.write(data_model.target_tree)
```

The tree format shows element names, data types, and cardinality (min/max occurrences):

```
TimeSeries[0, None]:
    mRID[1, 1]: string
    businessType[1, 1]: NMTOKEN
    Available_Period[0, None]:
        timeInterval_start[1, 1]: string
        timeInterval_end[1, 1]: string
        resolution[1, 1]: duration
```

### Importing XML files

``` py title="Parse and import an XML file" linenums="1"
document = data_model.parse_xml(xml_file="path/to/file.xml")
document.insert_into_target_tables()
```

By default, XML files are not validated against the schema. Enable validation if you need to verify file integrity.

[`Document.insert_into_target_tables`](api/document.md#xml2db.document.Document.insert_into_target_tables) handles creating tables, staging data, merging, and cleanup automatically.

!!! note
    To attach metadata to each loaded file (e.g. filename or timestamp), configure [`metadata_columns`](configuring.md#model-configuration) and pass values via the `metadata` argument:

    ``` py
    document = data_model.parse_xml(
        xml_file="path/to/file.xml",
        metadata={"input_file_path": "path/to/file.xml"},
    )
    ```

!!! note "Loading multiple files in one database operation"
    Accumulate records from multiple files in memory before a single insert to reduce database round-trips:

    ``` py
    flat_data = None
    for xml_file in files:
        document = data_model.parse_xml(
            xml_file=xml_file,
            metadata={"input_file_path": xml_file},
            flat_data=flat_data,
        )
        flat_data = document.data
    document.insert_into_target_tables()
    ```

## Getting data back to XML

Data can be extracted from the database back to XML, primarily for round-trip testing:

``` py title="Extract data back to XML" linenums="1"
document = data_model.extract_from_database(
    root_select_where="xml2db_input_file_path='path/to/file.xml'",
)
document.to_xml("extracted_file.xml")
```
