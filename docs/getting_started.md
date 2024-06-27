# Getting started

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

At this stage, it is not required to provide a connection string and have an actual database set up, but it will be 
necessary if you want to use this [`DataModel`](api/data_model.md) to actually import data. You may need to install the
Python package of the connector you use in your `sqlalchemy` connection string (`psycopg2` in the example above).

You can provide an optional model configuration, which will allow forcing or preventing some schema simplification, set
columns types manually, etc. By default, some simplifications will be applied when possible, in order to limit the 
resulting data model complexity.

## Visualizing the data model

When you start from a new XML schema, we recommend that you first visualize the resulting data model and decide whether
it needs some tweaking. The simplest solution will be to generate a markdown page which contains a visual representation
of your schema (`data_model` being the [`DataModel`](api/data_model.md) object previously created):

``` py title="Write an Entity Relationship Diagram to a file" linenums="1"
with open(f"target_data_model_erd.md", "w") as f:
   f.write(data_model.get_entity_rel_diagram())
```

You can see an example of these diagrams on the [Introduction page](index.md).

The data model visualization uses [Mermaid](https://mermaid.js.org/syntax/entityRelationshipDiagram.html) to create an
"entity relationship diagram" which will show the tables created and the relationships between them. To visualize this,
you can for instance rely on [Pycharm IDE mermaid support](https://www.jetbrains.com/help/pycharm/markdown.html#diagrams).
GitHub will also natively support those.

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

Once you are happy with the data model created from previous steps, you are now ready to actually process XML files and
load their content to your database. It goes like this:

``` py title="Parse a XML file" linenums="1"
document = data_model.parse_xml(
    xml_file="path/to/file.xml",
)
document.insert_into_target_tables()
```

By default, the validity of your XML file will not be checked against the XML schema used to create your `data_model` 
object, which can be enabled if you are unsure that your XML files will be valid.

The [`Document.insert_into_target_tables`](api/document.md#xml2db.document.Document.insert_into_target_tables) method is
then all you need to load your data to the database.

Please read the [How it works](how_it_works.md) page to learn more about the process, which could help 
troubleshooting if need be.

!!! note
    `xml2db` can save metadata for each loaded XML file. These can be configured using the 
    [`metadata_columns` option](configuring.md#model-configuration) and create additional columns in the root table.
    It can be used for instance to save file name or loading timestamp.

## Getting back the data into XML

You can extract the data from the database into XML files. This was implemented primarily to be able to test the package
using "round trip" tests to and from the database.

``` py title="Extract data back to XML" linenums="1"
document = data_model.extract_from_database(
    root_select_where="xml2db_input_file_path='path/to/file.xml'",
)
document.to_xml("extracted_file.xml")
```
