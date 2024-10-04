# Loading XML files into a relational database

`xml2db` is a Python package which allows parsing and loading XML files into a relational database. It handles complex 
XML files which cannot be denormalized to flat tables, and works out of the box, without any custom mapping rules.

It can be used within an [Extract, Load, Transform](https://docs.getdbt.com/terms/elt) data pipeline pattern as it 
allows loading XML files into a relational data model which is very close from the source data, yet easy to work with.

Starting from an XSD schema which represents a given XML structure, `xml2db` builds a data model, i.e. a set of database 
tables linked to each other by foreign keys relationships. Then, it allows parsing and loading XML files into the 
database, and getting them back from the database into XML format if needed.

Loading XML files into a relational database with `xml2db` can be as simple as:

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

The data model created by `xml2db` will be close to the XSD schema. However, `xml2db` will perform a few systematic 
simplifications aimed at limiting the complexity of the resulting data model and the storage footprint. The resulting 
data model can be configured, but the above code will work out of the box, with reasonable defaults.

The raw data loaded into the database can then be processed if need be, using for instance [DBT](https://www.getdbt.com/),
SQL views or stored procedures aimed at extracting, correcting and formatting the data into more user-friendly tables.

This package uses `sqlalchemy` to interact with the database, so it should work with different database backends. 
Automated integration tests run against PostgreSQL, MySQL, MS SQL Server and DuckDB. You may have to install additional 
packages to connect to your database (e.g. `psycopg2` for PostgreSQL, `pymysql` for MySQL, `pyodbc` for MS SQL Server or
`duckdb_engine` for DuckDB).

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

`xml2db` is developed and used at the [French energy regulation authority (CRE)](https://www.cre.fr/) to process complex 
XML data.

Contributions are welcome, as well as bug reports, starting on the project's 
[issue page](https://github.com/cre-dev/xml2db/issues).
