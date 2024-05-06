# Xml2db

`xml2db` is a Python package which allows loading XML data into a relational database. It is designed to handle complex 
schemas which cannot be easily denormalized to a flat table, without any custom code.

It builds a data model (i.e. a set of database tables linked with foreign keys relationships) based on a XSD schema and
allows parsing and loading XML files into the database, and get them back to XML, if needed.

It is as simple as:

```python
from xml2db import DataModel

# Create a data model of tables with relations based on the XSD file
data_model = DataModel(
    xsd_file="path/to/file.xsd", 
    connection_string="postgresql+psycopg2://testuser:testuser@localhost:5432/testdb",
)
# Parse an XML file based on this XSD
document = data_model.parse_xml(
    xml_file="path/to/file.xml"
)
# Insert the document content into the database
document.insert_into_target_tables()
```

The data model will adhere closely to the XSD schema, but `xml2db` will perform simplifications aimed at limiting the 
complexity of the resulting data model and the storage footprint.

The raw data loaded into the database can then be processed using [DBT](https://www.getdbt.com/), SQL views or 
other tools aimed at extracting, correcting and formatting the data into more user-friendly tables.

`xml2db` is developed and used at the [French energy regulation authority (CRE)](https://www.cre.fr/) to process XML 
data.

This package uses `sqlalchemy` to interact with the database, so it should work with different database backends. 
Automated integration tests run against PostgreSQL, MySQL and MS SQL Server. `xml2db` does not work with SQLite. You may
have to install additional packages to connect to your database (e.g. `psycopg2` for PostgreSQL, `pymysql` for MySQL or 
`pyodbc` for MS SQL Server).

**Please read the [package documentation website](https://cre-dev.github.io/xml2db) for all the details!**

## Installation

The package can be installed, preferably in a virtual environment, using `pip`:

``` bash
pip install xml2db
```

## Testing

Running the tests requires installing additional development dependencies, after cloning the repo, with:

```bash
pip install -e .[tests,docs]
```

Run all tests with the following command:

```bash
python -m pytest
```

Integration tests require write access to a PostgreSQL or MS SQL Server database; the connection string is provided as an
environment variable `DB_STRING`. If you want to run only conversion tests that do not require a database you can run:

```bash
pytest -m "not dbtest"
`````

## Contributing

Contributions are more than welcome, as well as bug reports, starting with the project's 
[issue page](https://github.com/cre-dev/xml2db/issues).
