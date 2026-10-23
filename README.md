# Loading XML files into a relational database

`xml2db` is a Python package that parses and loads XML files into a relational database. It handles complex 
XML files which cannot be denormalized to flat tables, and works out of the box, without any custom mapping rules.

It fits naturally into an [Extract, Load, Transform](https://docs.getdbt.com/terms/elt) pipeline: it 
loads all the content of XML files into a relational data model that stays close to the source data while remaining
easy to query as flat database tables. Parsing XML is slow compared to SQL, so you do not need to decide upfront what
to extract: explore the loaded data, then build more user-friendly tables with [dbt](https://www.getdbt.com/), SQL
views, or stored procedures, and change them later without parsing the files again.

Starting from an XSD schema which represents a given XML structure, `xml2db` builds a data model, i.e. a set of database 
tables linked to each other by foreign keys relationships. Then, it allows parsing and loading XML files into the 
database, and getting them back from the database into XML format if needed.

This package uses `sqlalchemy` to interact with the database, so it should work with different database backends. 
Automated integration tests run against PostgreSQL, MySQL, MS SQL Server and DuckDB. You may have to install additional 
packages to connect to your database (e.g. `psycopg2` or `psycopg` for PostgreSQL, `pymysql` or `mysqlclient` for
MySQL, `pyodbc` for MS SQL Server, or `duckdb-engine` for DuckDB). Through DuckDB, the loaded tables can also be
transformed and exported to SQLite, Parquet files or Delta Lake.

**Please read the [package documentation website](https://cre-dev.github.io/xml2db) for all the details!**

## When to use xml2db

| Situation | Usually enough | What xml2db adds |
|---|---|---|
| A few fields from flat, record-like XML | `pandas.read_xml`, a short `lxml` script, or the XML functions of your database | Little: these are simpler |
| One repeated record element with shallow nesting | XML readers that turn each record into a row, such as Spark's XML data source or DuckDB XML extensions | Normalized tables instead of nested columns to explode |
| Deep nesting, repeated elements at several levels, large XSD | Hand-written mappings, one per element | Tables, keys and loading code generated from the XSD, no mapping to maintain |
| Recurring feed of files following the same schema | A custom script per feed | The same load for every file, with redundant content stored once |
| Needs not settled yet: which fields, which aggregations | Extracting the fields you expect to need, and parsing the files again when needs change | Everything loaded once: new questions are answered with SQL |
| All the data must be kept, or written back to XML | Hand-written mappings, with the risk of dropping fields | Every element and attribute kept, with a round trip back to XML |

`xml2db` needs an XSD schema. See the documentation for an [example](https://cre-dev.github.io/xml2db/#from-xml-to-tables)
and for database-specific guides: [PostgreSQL](https://cre-dev.github.io/xml2db/databases/postgresql/),
[SQL Server](https://cre-dev.github.io/xml2db/databases/sql_server/),
[MySQL and MariaDB](https://cre-dev.github.io/xml2db/databases/mysql/),
[DuckDB](https://cre-dev.github.io/xml2db/databases/duckdb/),
[SQLite, Parquet and Delta Lake](https://cre-dev.github.io/xml2db/databases/other_targets/). To transform the loaded
data, see [Transform with dbt](https://cre-dev.github.io/xml2db/dbt/). To only generate SQL tables from an XSD, see
[XSD to SQL tables](https://cre-dev.github.io/xml2db/xsd_to_sql/).

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
