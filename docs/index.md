---
title: "Loading XML into a relational database"
---

# Loading XML into a relational database

`xml2db` is a Python package which allows parsing and loading XML files into a relational database:

* it maps automatically a XSD schema with a set of tables in the database
* it can handle complex XML files which cannot be denormalized into flat tables
* it works out of the box, without any custom mapping rules.

`xml2db` fits well within an [Extract, Load, Transform](https://docs.getdbt.com/terms/elt) data pipeline pattern: it 
loads XML files into a relational data model which is very close to the source data, yet easy to work with, being flat 
database tables.

## How to load XML files into a database

Loading XML files into a relational database with `xml2db` can be as simple as:

``` py title="Loading XML into a database" linenums="1" 
from xml2db import DataModel

# Create a DataModel object from an XSD file
data_model = DataModel(
    xsd_file="path/to/file.xsd", 
    connection_string="postgresql+psycopg2://testuser:testuser@localhost:5432/testdb",
)

# Parse an XML file based on this XSD schema
document = data_model.parse_xml(xml_file="path/to/file.xml")

# Load data into the database, creating target tables if need be
document.insert_into_target_tables()
```

The resulting data model will be very similar with the XSD schema. However, `xml2db` will perform automatically a few
simplifications aimed at limiting the complexity of the resulting data model and the storage footprint. The data model 
can be configured, but the above code will work out of the box for most schemas, with reasonable defaults.

The raw data loaded into the database can then be processed if need be, using for instance [DBT](https://www.getdbt.com/),
SQL views or stored procedures aimed at extracting, correcting and formatting the data into more user-friendly tables.

This package uses `sqlalchemy` to interact with the database, so it should work with different database backends. 
Automated integration tests run against PostgreSQL, MySQL, MS SQL Server and DuckDB. You may have to install additional 
packages to connect to your database (e.g. `psycopg2` for PostgreSQL, `pymysql` for MySQL, `pyodbc` for MS SQL Server or
`duckdb_engine` for DuckDB).

## How to visualize your data model 

`xml2db` can also generate automatically beautiful visualisations of your data models extracted from an XSD file. It 
uses [Mermaid](https://mermaid.js.org/syntax/entityRelationshipDiagram.html) to represent database tables and their 
relationships.

It is useful to visualize your data model in order to further [configure it](./configuring.md) if need be.

It looks like this:

```mermaid
erDiagram
    Unavailability_MarketDocument ||--o{ TimeSeries : "TimeSeries*"
    Unavailability_MarketDocument ||--|{ Reason : "Reason*"
    Unavailability_MarketDocument {
        string mRID
        string revisionNumber
        NMTOKEN type
        NMTOKEN process_processType
        dateTime createdDateTime
        string sender_MarketParticipant_mRID
        NMTOKEN sender_MarketParticipant_marketRole_type
        string receiver_MarketParticipant_mRID
        NMTOKEN receiver_MarketParticipant_marketRole_type
        string unavailability_Time_Period_timeInterval_start
        string unavailability_Time_Period_timeInterval_end
        NMTOKEN docStatus_value
    }
    TimeSeries ||--o{ Available_Period : "Available_Period*"
    TimeSeries ||--o{ Available_Period : "WindPowerFeedin_Period*"
    TimeSeries ||--o{ Asset_RegisteredResource : "Asset_RegisteredResource*"
    TimeSeries ||--o{ Reason : "Reason*"
    TimeSeries {
        string mRID
        NMTOKEN businessType
        string biddingZone_Domain_mRID
        string in_Domain_mRID
        string out_Domain_mRID
        date start_DateAndOrTime_date
        time start_DateAndOrTime_time
        date end_DateAndOrTime_date
        time end_DateAndOrTime_time
        NMTOKEN quantity_Measure_Unit_name
        NMTOKEN curveType
        string production_RegisteredResource_mRID
        string production_RegisteredResource_name
        string production_RegisteredResource_location_name
        NMTOKEN production_RegisteredResource_pSRType_psrType
        string production_RegisteredResource_pSRType_powerSystemResources_mRID
        string production_RegisteredResource_pSRType_powerSystemResources_name
        float production_RegisteredResource_pSRType_powerSystemResources_nominalP
    }
    Available_Period ||--|{ Point : "Point*"
    Available_Period {
        string timeInterval_start
        string timeInterval_end
        duration resolution
    }
    Point {
        integer position
        decimal quantity
    }
    Asset_RegisteredResource {
        string mRID
        string name
        NMTOKEN asset_PSRType_psrType
        string location_name
    }
    Reason {
        NMTOKEN code
        string text
    }
```

## How to contribute to this project

`xml2db` is developed and used at the [French energy regulation authority (CRE)](https://www.cre.fr/) to process complex
XML data.

Contributions are welcome, as well as bug reports, starting on the project's 
[issue page](https://github.com/cre-dev/xml2db/issues).

If you find this package useful, you can give it a star on [`xml2db`'s GitHub repo](https://github.com/cre-dev/xml2db)!
