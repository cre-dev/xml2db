---
title: "CLI usage"
description: "Reference for the xml2db command-line interface: import XML files, render ERDs and DDL, and launch the interactive browser explorer."
---

# CLI usage

The `xml2db` CLI provides three subcommands: `import`, `render`, and `serve`.

## xml2db import

Parse an XML file and load it into a database.

```
xml2db import XML_FILE XSD_FILE --connection-string DSN [options]
```

**Positional arguments:**

| Argument | Description |
|---|---|
| `XML_FILE` | Path to the XML file to import |
| `XSD_FILE` | Path to the XSD schema file |

**Options:**

| Option | Description |
|---|---|
| `--connection-string DSN`, `-d DSN` | SQLAlchemy connection string (required) |
| `--config FILE`, `-c FILE` | YAML model config file |
| `--db-schema SCHEMA` | Database schema to use |
| `--metadata KEY=VALUE`, `-m KEY=VALUE` | Metadata values for `metadata_columns` (repeatable) |
| `--short-name NAME` | Data model short name (default: `DocumentRoot`) |
| `--no-iterparse` | Use the recursive parser instead of iterparse (higher memory usage) |
| `--recover` | Attempt to parse malformed XML |
| `--validate` | Validate the XML against the schema before importing |

**Example:**

```bash
xml2db import file.xml schema.xsd \
    --connection-string "postgresql+psycopg2://user:pw@host/db" \
    --config model_config.yml \
    --metadata source=file.xml
```

On success, the command prints the number of rows inserted and already-existing (deduplicated), with per-phase timings.

## xml2db render

Print an ERD, source/target tree, or DDL to stdout or a file, without starting a server.

```
xml2db render XSD_FILE [options]
```

**Positional arguments:**

| Argument | Description |
|---|---|
| `XSD_FILE` | Path to the XSD schema file |

**Options:**

| Option | Description |
|---|---|
| `--config FILE`, `-c FILE` | YAML model config file |
| `--db-names` | Use physical database identifiers in the ERD instead of logical names |
| `--db-type BACKEND` | Database backend for DDL output (`postgresql`, `mssql`, `mysql`, ...) |
| `--format FORMAT`, `-f FORMAT` | Output format: `erd` (default), `target-tree`, `source-tree`, or `ddl` |
| `--output FILE`, `-o FILE` | Write output to a file instead of stdout |
| `--short-name NAME` | Data model short name (default: `DocumentRoot`) |

**Examples:**

```bash
xml2db render schema.xsd --format erd
xml2db render schema.xsd --format target-tree
xml2db render schema.xsd --format source-tree
xml2db render schema.xsd --format ddl --db-type postgresql
xml2db render schema.xsd --format erd --output diagram.md
```

## xml2db serve

Launch an interactive schema explorer in the browser.

```
xml2db serve XSD_FILE [options]
```

The explorer shows four tabs: ERD, target tree, source tree, and DDL. The left panel is a YAML config editor with autocomplete for table names, field names, and all config options. Edits trigger an automatic rebuild. The **Save** button writes the config back to disk.

**Positional arguments:**

| Argument | Description |
|---|---|
| `XSD_FILE` | Path to the XSD schema file |

**Options:**

| Option | Description |
|---|---|
| `--config FILE`, `-c FILE` | YAML model config file to load on startup; Save writes it back to this path (default: `model_config.yml`) |
| `--db-type BACKEND` | Database backend for the DDL tab (`postgresql`, `mssql`, `mysql`, ...) |
| `--no-browser` | Do not open the browser automatically |
| `--port PORT`, `-p PORT` | HTTP port (default: `8765`) |
| `--short-name NAME` | Data model short name (default: `DocumentRoot`) |

**Example:**

```bash
xml2db serve schema.xsd --config model_config.yml --db-type postgresql
```

See [Getting started](getting_started.md) for a walkthrough of the explorer.
