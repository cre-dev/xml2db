# Introduction

`xml2db` is a Python package which allows loading XML files into a relational database, even for complex schemas which 
cannot be denormalized to a flat table, without having to write any custom code.

It builds a data model (i.e. a set of database tables linked to each other by foreign keys relationships) based on an 
XSD schema. Then, it allows parsing and loading XML files into the database, and getting them back from the database 
into XML if needed.

## Simple example

It is as simple as:

```python
from xml2db import DataModel

data_model = DataModel(
    xsd_file="path/to/file.xsd", 
    connection_string="postgresql+psycopg2://testuser:testuser@localhost:5432/testdb",
)
document = data_model.parse_xml(xml_file="path/to/file.xml")
document.insert_into_target_tables()
```

The data model will adhere closely to the XSD schema, but `xml2db` will perform a few systematic simplifications aimed 
at limiting the complexity of the resulting data model and the storage footprint.

The raw data loaded into the database can then be processed if need be, using for instance [DBT](https://www.getdbt.com/),
SQL views or stored procedures aimed at extracting, correcting and formatting the data into more user-friendly tables.

`xml2db` is developed and used at the [French energy regulation authority (CRE)](https://www.cre.fr/) to process complex XML data.

This package uses `sqlalchemy` to interact with the database, so it should work with different database backends. It has
been tested against PostgreSQL and MS SQL Server. It currently does not work with SQLite. You may have to install 
additional packages to connect to your database (e.g. `pyodbc` which is the default connector for MS SQL Server, or 
`psycopg2` for PostgreSQL).

## Data model visualization

`xml2db` can also generate automatically beautiful visualisations of your data models, using [Mermaid](https://mermaid.js.org/syntax/entityRelationshipDiagram.html),
like this one:

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

## Contributing

Contributions are welcome, as well as bug reports, starting on the project's 
[issue page](https://github.com/cre-dev/xml2db/issues).

    