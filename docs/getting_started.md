---
title: "Getting started"
description: "Step-by-step guide to installing xml2db, creating a DataModel from an XSD file, importing XML into a relational database, and visualizing the resulting data model."
---

# Getting started

This guide walks you through installing xml2db, creating a data model from an XSD schema, loading XML files into a relational database, and exporting data back to XML.

## Installation

The package can be installed, preferably in a virtual environment, using `pip`:

``` bash
pip install xml2db
```

!!! note
    If you want to contribute to the development of `xml2db`, clone the git repository and then install it in your 
    virtual environment in editable mode. From the project's directory, run:
    
    ``` bash
    pip install -e .[docs,tests]
    ```

## Reading an XML schema

Start from an XSD schema file that you will read with `xml2db` to create a [`DataModel`](api/data_model.md) object:

``` py title="Create a DataModel object" linenums="1"
from xml2db import DataModel

data_model = DataModel(
    xsd_file="path/to/file.xsd",
    db_schema="source_data", # the name of the database target schema
    connection_string="postgresql+psycopg2://testuser:testuser@localhost:5432/testdb",
    model_config={},
)
```

A connection string and database are not required at this stage, but both are needed to actually import data. You
may need to install a connector package (e.g. `psycopg2` or `psycopg` for PostgreSQL, `pymysql` or `mysqlclient` for
MySQL, `pyodbc` for SQL Server, `duckdb-engine` for DuckDB). See
[How it works](how_it_works.md#bulk-loading) for which drivers enable native bulk loading.

The optional `model_config` controls schema simplifications, column types, and more. By default, some simplifications
are applied to reduce data model complexity.

## Visualizing the data model

When starting from a new XML schema, we recommend visualizing the data model first to decide whether any tweaking is
needed. Generate a Markdown file with a visual representation of your schema (`data_model` being the
[`DataModel`](api/data_model.md) object previously created):

``` py title="Write an Entity Relationship Diagram to a file" linenums="1"
with open(f"target_data_model_erd.md", "w") as f:
   f.write(data_model.get_entity_rel_diagram())
```

You can see an example of these diagrams on the [Introduction page](index.md).

The diagram uses [Mermaid](https://mermaid.js.org/syntax/entityRelationshipDiagram.html) to show the tables and their
relationships. [PyCharm](https://www.jetbrains.com/help/pycharm/markdown.html#diagrams) and GitHub both render Mermaid
diagrams natively.

You can also visualize your model in a tree-like text mode. In this format, you can visualize the raw, untouched XML
schema, as well as the simplified one (we call it "target" model):

``` py title="Write source tree and target tree to a file" linenums="1"
with open(f"source_tree.txt", "w") as f:
    f.write(data_model.source_tree)

with open(f"target_tree.txt", "w") as f:
    f.write(data_model.target_tree)
```

It will write something like this:

```
...
docStatus_value[0, 1]: NMTOKEN
TimeSeries[0, None]:
    mRID[1, 1]: string
    businessType[1, 1]: NMTOKEN
    quantity_Measure_Unit.name[1, 1]: NMTOKEN
    curveType[1, 1]: NMTOKEN
    Available_Period[0, None]:
        timeInterval_start[1, 1]: string
        timeInterval_end[1, 1]: string
        resolution[1, 1]: duration
        Point[1, None]:
            position[1, 1]: integer
            quantity[1, 1]: decimal
    WindPowerFeedin_Period[0, None]:
        timeInterval_start[1, 1]: string
        timeInterval_end[1, 1]: string
...
```

This gives you the elements names, data type and cardinality (min/max number of children elements). 

It is useful to visualize your data model in order to [configure it](configuring.md) to suit your needs.

## Importing XML files

Once the data model looks right, load XML files as follows:

``` py title="Parse an XML file" linenums="1"
document = data_model.parse_xml(
    xml_file="path/to/file.xml",
)
document.insert_into_target_tables()
```

By default, XML files are not validated against the schema. Enable validation if you need to verify file integrity.

[`Document.insert_into_target_tables`](api/document.md#xml2db.document.Document.insert_into_target_tables) is all you
need to load data into the database.

See the [How it works](how_it_works.md) page for a deeper explanation of the loading process.

!!! note
    `xml2db` can save metadata for each loaded XML file. These can be configured using the 
    [`metadata_columns` option](configuring.md#model-configuration) and create additional columns in the root table.
    It can be used for instance to save file name or loading timestamp.

    Actual values need to be passed to [`DataModel.parse_xml`](api/data_model.md#xml2db.model.DataModel.parse_xml) for 
    each parsed documents, as a `dict`, using the `metadata` argument.

!!! note "Loading multiple XML files in one database operation"
    By default, each `parse_xml` + `insert_into_target_tables` call is an independent database operation. When you have
    many small XML files to load, you can instead accumulate all of them in memory first and insert them in a single
    batch, which reduces the number of database round-trips.

    Pass the `flat_data` from the previous document into the next `parse_xml` call to accumulate records:

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

    Note that each file can carry its own `metadata` values (e.g. the file name or a loading timestamp), which will be
    stored per root record in the columns defined by
    [`metadata_columns`](configuring.md#model-configuration).



## Getting back the data into XML

Data can be extracted from the database back to XML, primarily for round-trip testing.

``` py title="Extract data back to XML" linenums="1"
document = data_model.extract_from_database(
    root_select_where="xml2db_input_file_path='path/to/file.xml'",
)
document.to_xml("extracted_file.xml")
```
