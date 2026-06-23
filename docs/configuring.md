---
title: "Configuring your data model"
description: "Configure xml2db's data model via model_config: override column types, control field elevation, adjust deduplication, simplify XSD choice groups, and add custom indexes."
---

# Configuring your data model

The data model is derived automatically from an XSD file. Each `complexType` becomes a table, columns come from `simpleType` elements and attributes, and `xml2db` applies a few simplifications by default to reduce complexity.

Options apply at three levels: model, table, and field.

!!! tip
    Start without any configuration, visualize the data model, then add options as needed. See the [Getting started](getting_started.md) page for how to visualize data models.

## Interactive configuration with the CLI

The easiest way to configure the model is the browser explorer:

``` bash
xml2db serve schema.xsd --config model_config.yml
```

The left panel is a YAML editor with autocomplete for all config keys, table names from your XSD, and field names. Edit the config and the ERD, tree views, and DDL update automatically. Click **Save** to write the config back to disk.

## Config file format

The config can be written as a YAML file and passed with `--config` (CLI) or `load_config()` (Python API):

``` yaml title="model_config.yml"
row_numbers: false
record_hash_column_name: record_hash
metadata_columns:
  - name: input_file_path
    type: String(256)
tables:
  my_table:
    reuse: false
    choice_transform: false
    fields:
      my_column:
        type: String(100)
        rename: col_name
        transform: skip
```

SQLAlchemy type names in YAML are strings like `String(256)`, `Integer`, `DateTime(timezone=True)`. The full list of supported names: `String`, `Text`, `Integer`, `BigInteger`, `SmallInteger`, `Float`, `Double`, `Numeric`, `Boolean`, `DateTime`, `Date`, `Time`, `LargeBinary`, `JSON`, `Uuid`.

Keys that require Python callables (`document_tree_hook`, `document_tree_node_hook`, `record_hash_constructor`) cannot be set in a YAML file. Pass a Python dict directly in that case.

## Python dict config

For programmatic use, or when you need callable hooks or SQLAlchemy type instances, pass a dict to `DataModel`:

```py title="Model config general structure" linenums="1"
from xml2db import DataModel
import sqlalchemy

model_config = {
    "document_tree_hook": None,
    "document_tree_node_hook": None,
    "row_numbers": False,
    "as_columnstore": False,
    "metadata_columns": [],
    "tables": {
        "table1": {
            "reuse": True,
            "choice_transform": False,
            "as_columnstore": False,
            "fields": {
                "my_column": {
                    "type": None,  # default type
                }
            },
            "extra_args": [],
        }
    },
}

data_model = DataModel(xsd_file="schema.xsd", model_config=model_config)
```

To load a YAML file into a Python dict, use `load_config`:

``` py
from xml2db import load_config
model_config = load_config("model_config.yml")
```

## Model configuration

The following options can be passed as top-level keys of the model configuration `dict`:

* `document_tree_hook` (`Callable`): sets a hook function which can modify the data extracted from the XML. It gives direct
access to the underlying tree data structure just before it is extracted to be loaded to the database. This can be used,
for instance, to prune or modify some parts of the document tree before loading it into the database. The document tree
should of course stay compatible with the data model. For simply excluding a field from the schema without custom logic,
the declarative [`"transform": "skip"`](#skipping-fields) option is simpler.
* `document_tree_node_hook` (`Callable`): sets a hook function which can modify the data extracted from the XML. It is
similar with `document_tree_hook`, but it is called as soon as a node is completed, not waiting for the entire parsing to
finish. It is especially useful if you intend to filter out some nodes and reduce memory footprint while parsing. For
straightforward field exclusion, see [`"transform": "skip"`](#skipping-fields).
* `row_numbers` (`bool`): adds `xml2db_row_number` columns either to `n-n` relationships tables, or directly to data tables when 
deduplication of rows is opted out. This allows recording the original order of elements in the source XML, which is not
always respected otherwise. It was implemented primarily for round-trip tests, but could serve other purposes. The 
default value is `False` (disabled).
* `as_columnstore` (`bool`): for MS SQL Server, create clustered columnstore indexes on all tables. This can be also set up at
the table level for each table. However, for `n-n` relationships tables, this option is the only way to configure the
clustered columnstore indexes. The default value is `False` (disabled).
* `metadata_columns` (`list`): a list of extra columns that you want to add to the root table of your model. This is
useful for instance to add the name of the file which has been parsed, or a timestamp, etc. Columns should be specified
as dicts, the only required keys are `name` and `type` (a SQLAlchemy type object); other keys will be passed directly
as keyword arguments to `sqlalchemy.Column`. Actual values need to be passed to 
[`DataModel.parse_xml`](api/data_model.md#xml2db.model.DataModel.parse_xml) for each 
parsed documents, as a `dict`, using the `metadata` argument.
* `record_hash_column_name`: the column name to use to store records hash data (defaults to `xml2db_record_hash`).
* `record_hash_constructor`: a function used to build a hash, with a signature similar to `hashlib` constructor 
functions (defaults to `hashlib.sha1`).
* `record_hash_size`: the byte size of the record hash (defaults to 20, which is the size of a `sha-1` hash).

## Fields configuration

These configuration options are defined for a specific field of a specific table. A "field" refers to a column in the
table, or a child table.

### Source names vs target names

Field names in `model_config` come from two different points in the processing pipeline, and **which one to use depends on the config key**:

| Config key | Name to use | Where to look |
|---|---|---|
| `transform` | **Source name**: the original XSD element or relation name, before any simplification | **Source tree** tab |
| `type`, `rename` | **Target name**: the logical column name after elevation and prefixing | **Target tree** tab |

**Why this matters:** elevation (the default for small mandatory children) collapses a child relation into prefixed columns in the parent. For example, if `timeInterval` is elevated, the target model has `timeInterval_start` and `timeInterval_end` — but `timeInterval` itself no longer appears in the target tree. To opt out of elevation you configure `fields.timeInterval.transform: false` using the **source name**. To rename an elevated result you configure `fields.timeInterval_start.rename: "start"` using the **target name**.

If a field is not elevated (a direct column or a kept relation), its source and target names are identical and there is no ambiguity.

The browser explorer autocomplete (`xml2db serve`) offers both source and target field names and labels each accordingly.

### Data types

!!! note "Uses target name"
    Use the field name as it appears in the **Target tree** tab.

By default, the data type defined in the database table for each column is based on a mapping between the data type 
indicated in the XSD and a corresponding `sqlalchemy` type implemented in the following three methods:

??? info "Default: `DatabaseDialect.column_type`"
    ::: xml2db.dialect.base.DatabaseDialect.column_type

??? info "MySQL: `MySQLDialect.column_type`"
    ::: xml2db.dialect.mysql.MySQLDialect.column_type

??? info "MSSQL: `MSSQLDialect.column_type`"
    ::: xml2db.dialect.mssql.MSSQLDialect.column_type

You may override this mapping by specifying a column type for any field in the model config. Custom column types are 
defined as `sqlalchemy` types and will be passed to the `sqlalchemy.Column` constructor as is.

!!! example
    If the XSD mentions the `integer` type for column `my_column` in table `my_table`, by default, `xml2db`will map 
    to `sqlalchemy.Integer`. For instance, if you want it to map to `mssql.BIGINT` instead, you can provide this config:

    ```python
    import xml2db
    from sqlalchemy.dialects import mssql
    
    model_config = {
        "tables": {
            "my_table": {
                "fields": {
                    "my_column": {
                        "type": mssql.BIGINT
                    }
                }
            },
        },
    }
    
    data_model = xml2db.DataModel(
        xsd_file="path/to/file.xsd", db_schema="my_schema", model_config=model_config
    )
    ```
    
    You can infer `my_table` and `my_column` when visualizing the data model.

### Renaming columns

!!! note "Uses target name"
    Use the field name as it appears in the **Target tree** tab. For elevated fields, this is the prefixed name (e.g. `orderperson_name`), not the original child relation name.

The physical database column name for any field can be overridden while keeping the original XML element name as the
internal logical key. This is useful when XSD element names are awkward, conflict with reserved SQL words, or need to
follow a naming convention that differs from the source schema.

The rename applies to both the target table and the staging table. All internal references (data dict keys, foreign key
lookups, merge statements) continue to use the original logical name, so only the visible DB column name changes.

Configuration: `"rename":` `"new_column_name"` (no default; omit to keep the original name)

!!! example
    Rename the `orderid` attribute to `order_id` in the `shiporder` table:
    ```python
    model_config = {
        "tables": {
            "shiporder": {
                "fields": {
                    "orderid": {"rename": "order_id"}
                }
            }
        }
    }
    ```

    Elevated fields (those pulled up from a child table) are renamed using their prefixed name in the parent table:
    ```python
    model_config = {
        "tables": {
            "shiporder": {
                "fields": {
                    "orderperson_name": {"rename": "contact_name"}
                }
            }
        }
    }
    ```

### Joining values for simple types

!!! note "Uses source name"
    Use the field name as it appears in the **Source tree** tab.

By default, XML simple type elements with types in `["string", "date", "dateTime", "NMTOKEN", "time", "base64Binary", "decimal"]` and max 
occurrences >= 1 are joined in one column as comma separated values and optionally wrapped in double quotes if they 
contain commas (an Excel-like csv format, which can be queried with `LIKE` statements in SQL).

Configuration: `"transform":` `"join"` (default). It is not currently possible to use `False` to opt-out of an
automatically applied `join`, as it would require a complex process of adding a new table.

!!! example
    This config option is currently not very useful as it cannot be opted out.
    ``` python
    model_config = {
       "tables": {
           "my_table_name": {
               "fields": {
                   "my_field_name": {
                       "transform": "join"
                   }
               }
           }
       }
    }
    ```

### Skipping fields

!!! note "Uses source name"
    Use the field name as it appears in the **Source tree** tab.

Any field (column or relation) can be excluded from the data model entirely by setting its transform to `"skip"`.
The field will be absent from the target table schema and all data for it will be silently dropped during XML
parsing. This is useful for PII columns, large binary blobs, or fields that are irrelevant for analysis.

For a skipped relation, the child table is also pruned from the model unless it is referenced by another relation
elsewhere in the schema.

Configuration: `"transform": "skip"`

!!! warning
    Skipped fields are not recoverable: data for them is never stored. Round-trip XML reconstruction will omit
    any skipped field even when it was present in the source document.

!!! example
    Skip an optional scalar column and an optional relation:
    ```python
    model_config = {
        "tables": {
            "item": {
                "fields": {
                    "note": {"transform": "skip"},
                    "delivery": {"transform": "skip"},
                }
            }
        }
    }
    ```

### Elevate children to upper level

!!! note "Uses source name"
    Use the child relation name as it appears in the **Source tree** tab (the parent's field pointing to the child, before any elevation). This name may not appear in the Target tree at all if default elevation has already collapsed it.

A mandatory child (min occurrences = 1, i.e. `[1, 1]`) is always elevated to its parent by default, as long as it
is not involved in a 1-n relationship elsewhere in the schema.

An optional child (`[0, 1]`) is also elevated by default if it has 4 or fewer simple-type columns (relation fields
are not counted), and again only when it is not involved in a 1-n relationship elsewhere.

This behaviour can be disabled, or forced for larger children (more than 4 simple-type columns), using:

`"transform":` `"elevate"` (default) or `"elevate_wo_prefix"` or `False` (disable).

By default, the elevated field is prefixed with the child's name to clarify its origin and avoid name collisions.
Use `"elevate_wo_prefix"` to skip the prefix.

For example, complex child `timeInterval` with 2 fields of max occurrence 1, before elevation...
```shell
# Child table
timeInterval[1, 1]:
    start[1, 1]: string
    end[1, 1]: string
```

... and after elevation (with prefix):
```shell
# Parent fields
timeInterval_start[1, 1]: string
timeInterval_end[1, 1]: string
```

!!! example
    Force "elevation" of a complex type to its parent:
    ``` python
    model_config = {
        "tables": {
            "contract": {
                "fields": {
                    "docStatus": {
                        "transform": "elevate"
                    }
                }
            }
        }
    }
    ```

## Tables configuration

### Simplify "choice groups"

In XML schemas, choice groups are common: only one of the possible children may be present at a time.

This section covers choice groups of simple elements only (not complex types). The straightforward conversion creates
one column per option, of which only one will be non-`NULL` for each record.

If there are more than 2 possible choice options and the simple elements are of the same type, they can be transformed 
into two columns:

* `type` with the name of the element
* `value` with its value

Example of choice child in a table, before...
```shell
idOfMarketParticipant[1, 1] (choice):
   lei[1, 1]: string
   bic[1, 1]: string
   eic[1, 1]: string
   gln[1, 1]: string
```

... and after choice transformation:
```shell
idOfMarketParticipant[1, 1] (choice):
   type[1, 1]: string  # with possible values: ["lei", "bic", "eic", "gln"]
   value[1, 1]: string
```

This simplification is applied automatically when there are more than 2 options of the same data type. It can be
forced on or disabled explicitly with the following option:

`"choice_transform":` `True` (force on) or `False` (disable)

!!! example
    Disable choice group simplification for a choice group:
    ``` python
    model_config = {
        "tables": {
            "my_table_name": {
                "choice_transform": False
            }
        }
    }
    ```

### Deduplication

By default, `xml2db` deduplicates elements (storing each unique element only once), which is particularly useful
when an XML element specifies a feature shared by many other elements.

This is done using a hash of each node in the XML file, which includes recursively all its children. The detailed 
process is described in the [how it works](how_it_works.md) page.

The implication is that relationships with 1-1 or 1-n cardinality in the XML schema are converted by default into 
n-1 and n-n relationships in the database. For n-n, relationships, it means that there is an additional relationship
table which has foreign keys relations to both tables in the relationship.

Disable deduplication if you expect mostly unique elements and want to avoid the extra join table. The `1-n`
relationship is then modelled with a plain foreign key to the parent, which simplifies the schema but stores duplicate
records.

Configuration: `"reuse":` `True` (default) or `False` (disable)

!!! example
    Disabling deduplication for a given table:
    ``` python
    model_config = {
        "tables": {
            "my_table": {"reuse": False}
        }
    }
    ```

### Columnstore Clustered Index

With MS SQL Server database backend, `xml2db` can create 
[Clustered Columnstore indexes](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/columnstore-indexes-overview?view=sql-server-ver16#clustered-columnstore-index)
on tables. However, for `n-n` relationships tables, this option needs to be set globally (see below). The default value 
is `False` (disabled).

### Extra arguments

Extra arguments can be passed to `sqlalchemy.Table` constructors, for instance if you want to customize indexes. These
can be passed in an iterable (e.g. `tuple` or `list`) which will be simply unpacked into the `sqlalchemy.Table` 
constructor when building the table.

Configuration: `"extra_args": []` (default)

!!! example
    Adding an index on a specific column:
    ``` python
    model_config = {
        "tables": {
            "my_table": {
                "extra_args": [sqlalchemy.Index("my_index", "my_column1", "my_column2")],
            }
        }
    }
    ```
