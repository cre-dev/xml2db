# Loading XML files into a relational database

`xml2db` is a Python package that parses and loads XML files into a relational database. It handles complex 
XML files which cannot be denormalized to flat tables, and works out of the box, without any custom mapping rules.

It fits naturally into an [Extract, Load, Transform](https://docs.getdbt.com/terms/elt) pipeline: it 
loads XML files into a relational data model that stays close to the source data while remaining easy to query as 
flat database tables. The raw data can then be transformed using [DBT](https://www.getdbt.com/), SQL views, or stored procedures to produce
more user-friendly tables.

Starting from an XSD schema which represents a given XML structure, `xml2db` builds a data model, i.e. a set of database 
tables linked to each other by foreign keys relationships. Then, it allows parsing and loading XML files into the 
database, and getting them back from the database into XML format if needed.

This package uses `sqlalchemy` to interact with the database, so it should work with different database backends. 
Automated integration tests run against PostgreSQL, MySQL, MS SQL Server and DuckDB. You may have to install additional 
packages to connect to your database (e.g. `psycopg2` or `psycopg` for PostgreSQL, `pymysql` or `mysqlclient` for
MySQL, `pyodbc` for MS SQL Server, or `duckdb-engine` for DuckDB).

**Please read the [package documentation website](https://cre-dev.github.io/xml2db) for all the details!**

## Installation

The package can be installed, preferably in a virtual environment, using `pip`:

``` bash
pip install xml2db
```

## CLI

After installation, `xml2db` is available as a command-line tool with three subcommands.

Explore your XSD schema and configure the data model interactively in a browser:

```bash
xml2db serve path/to/schema.xsd
```

This opens a page with an Entity Relationship Diagram, source/target tree views, DDL output, and a live YAML config 
editor with autocomplete.

Import an XML file directly from the command line:

```bash
xml2db import file.xml schema.xsd \
    --connection-string "postgresql+psycopg2://user:pw@host/db" \
    --config model_config.yml
```

Render the ERD, trees, or DDL to stdout or a file without starting a server:

```bash
xml2db render schema.xsd --format erd
xml2db render schema.xsd --format ddl --db-type postgresql
```

See the [CLI reference](https://cre-dev.github.io/xml2db/cli/) for all options.

## Python API

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
