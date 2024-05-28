# Configuring your data model

The data model in the database is derived automatically from a XML schema definition file (XSD) you provide. It is a set
of tables linked by foreign keys relationships. Basically, each `complexType` of the XML schema definition corresponds 
to a table in the target database data model. Each table is named after the first element name of this type, with 
de-duplication if needed. Columns in a table corresponds to `simpleType` elements within a complex type and its 
attributes. Columns are named after the names of children XML elements or attributes.

`xml2db` applies a few simplifications to the original data model by default, but they can also be opted-out or forced 
through the configuration `dict` provided to the `DataModel` constructor.

The column types can also be configured to override the default type mapping, using `sqlalchemy` types.

!!! tip
    We recommend that you first build the data model without any configuration, visualize it as a text tree or ER 
    diagram (see the [Getting started](getting_started.md) page for directions on how to visualize data models) and 
    then adapt the configuration if need be.

Configuration options are described below.  

## Field level config

These configuration options are defined for a specific field of a specific table. A "field" refers to a column in the
table, or a child table.

### Data types

By default, the data type defined in the database table for each column is based on a mapping between the data type 
indicated in the XSD and a corresponding `sqlalchemy` type implemented in the following three functions:

??? info "Default: `types_mapping_default`"
    ::: xml2db.table.column.types_mapping_default

??? info "MySQL: `types_mapping_mysql`"
    ::: xml2db.table.column.types_mapping_mysql

??? info "MSSQL: `types_mapping_mssql`"
    ::: xml2db.table.column.types_mapping_mssql

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

### Joining values for simple types

By default, XML simple type elements with types in `["string", "date", "dateTime", "NMTOKEN", "time"]` and max 
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

### Elevate children to upper level

If a complex child element has a minimum and maximum occurrences number of 1 and 1 respectively, it can be "pulled" up 
to its parent element. This behaviour will always be applied by default.

If a complex child element has a minimum and maximum occurrences number of 0 and 1 respectively, it can also be "pulled"
up to its parent element fields. This is applied by default if the child has less than 5 fields, because otherwise it
could clutter the parent element with many columns that will often be all `NULL`.

This simplification can be opted out using a configuration option, and forced in the case of a child with more than 5
fields, using the following option:

`"transform":` `"elevate"` (default) or `"elevate_wo_prefix"` or `False` (disable).

By default, the elevated field name is prefixed with the name of the complex child so its origin is clear and to prevent 
duplicated names, but this prefixing can be avoided with the value `"elevate_wo_prefix"`.

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

## Table level config

### Simplify "choice groups"

In XML schemas, choice groups are quite frequent. It means that only one of its possible children types should be 
present. 

Here we consider only choice groups of simple elements (not complex types). The naive way to convert this to a table is
to create one column for each possible choice, of which only one will have a non `NULL` value for each record.

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

This simplification is applied by default when there are more than 2 options of the same data type, but it can be opted
in or out otherwise, with the following option: 

`"choice_transform":` `True` (default) or `False` (disable)

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

By default, `xml2db` will try to deduplicate elements (store identical element only once in the database) in order to
reduce storage footprint, which is particularly relevant for "feature" fields in XML schemas, meaning when a XML element 
specify a feature as a child element, which is shared with many other elements.

This is done using a hash of each node in the XML file, which includes recursively all its children. The detailed 
process is described in the [how it works](how_it_works.md) page.

The implication is that relationships with 1-1 or 1-n cardinality in the XML schema are converted by default into 
n-1 and n-n relationships in the database. For n-n, relationships, it means that there is an additional relationship
table which has foreign keys relations to both tables in the relationship.

This behaviour can be opted-out, for instance if you know that there will be mostly unique elements and you prefer not
having the additional relationship table. The 1-n relationship will be modelled using only a foreign key to the parent, 
without an intermediate table holding the relationship, which makes the data model simpler, and maybe some queries 
faster, but stores more records in case of duplicated records.

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

Configuration: `"as_columnstore":` `False` (default) or `True`

## Global options

These options can be passed as a top-level keys of the model configuration `dict`:

* `document_tree_hook` (`Callable`): sets a hook function which can modify the data extracted from the XML. It gives direct
access to the underlying tree data structure just before it is extracted to be loaded to the database. This can be used,
for instance, to prune or modify some parts of the document tree before loading it into the database. The document tree
should of course stay compatible with the data model.
* `row_numbers` (`bool`): adds `xml2db_row_number` columns either to `n-n` relationships tables, or directly to data tables when 
deduplication of rows is opted out. This allows recording the original order of elements in the source XML, which is not
always respected otherwise. It was implemented primarily for round-trip tests, but could serve other purposes. The 
default value is `False` (disabled).
* `as_columnstore` (`bool`): for MS SQL Server, create clustered columnstore indexes on all tables. This can be also set up at
the table level for each table. However, for `n-n` relationships tables, this option is the only way to configure the
clustered columnstore indexes. The default value is `False` (disabled).