---
title: "Transform XML data with dbt"
description: "Use dbt on top of xml2db tables: keep all the XML data as a raw layer, flatten it with SQL models, and build incremental models filtered on keys."
---

# Transform XML data with dbt

`xml2db` loads XML files into tables that stay close to the XSD. These tables are a raw layer: they keep all the
source data, and [dbt](https://www.getdbt.com/) builds the tables people query on top of them, with SQL models that
are versioned, tested and documented.

Parsing XML is the slow part of the pipeline. Once the files are loaded, changing a model and rebuilding it only runs
SQL in the database, so you can start with a few models and add others as questions come, without parsing the files
again.

The examples below use the invoices schema of the [introduction](index.md#from-xml-to-tables). They were tested with
dbt 1.12 on DuckDB (`dbt-duckdb`) and PostgreSQL (`dbt-postgres`). Adapters also exist for SQL Server and other
databases.

## Loading into a raw schema

Load the files into a dedicated schema, and record the file name in a [metadata column](configuring.md#model-configuration):

``` py title="load.py" linenums="1"
import sqlalchemy
from xml2db import DataModel

data_model = DataModel(
    xsd_file="invoices.xsd",
    connection_string="duckdb:///warehouse.duckdb",
    db_schema="xml_raw",
    model_config={
        "metadata_columns": [{"name": "input_file_path", "type": sqlalchemy.String(256)}]
    },
)
for xml_file in xml_files:
    data_model.parse_xml(xml_file, metadata={"input_file_path": xml_file}).insert_into_target_tables()
```

Declare the xml2db tables as dbt sources, and write dbt models to another schema:

``` yaml title="models/staging/sources.yml"
sources:
  - name: xml2db
    schema: xml_raw
    tables:
      - name: invoices
      - name: invoices_invoice
      - name: invoice
      - name: invoice_line
      - name: line
```

``` yaml title="profiles.yml"
invoices:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: warehouse.duckdb
      schema: analytics
```

## Staging models

Staging models rename columns and fix types. `xml2db` stores XSD `date` values as text, since they may carry a time
zone, and decimals as floating point numbers by default:

``` sql title="models/staging/stg_invoice.sql"
select
    pk_invoice,
    id as invoice_id,
    cast(date as date) as invoice_date,
    customer_name,
    customer_country
from {{ source('xml2db', 'invoice') }}
```

``` sql title="models/staging/stg_line.sql"
select
    pk_line,
    sku,
    quantity,
    cast(price as decimal(12, 2)) as price
from {{ source('xml2db', 'line') }}
```

## Flattening

Repeated elements are linked through relationship tables such as `invoice_line`. Joining through them gives one row
per invoice line:

``` sql title="models/marts/fct_invoice_lines.sql"
{{ config(materialized='incremental') }}

select
    i.pk_invoice,
    i.invoice_id,
    i.invoice_date,
    i.customer_name,
    l.sku,
    l.quantity,
    l.price,
    l.quantity * l.price as amount
from {{ ref('stg_invoice') }} as i
join {{ source('xml2db', 'invoice_line') }} as il on il.fk_invoice = i.pk_invoice
join {{ ref('stg_line') }} as l on l.pk_line = il.fk_line
{% if is_incremental() %}
where i.pk_invoice > (select coalesce(max(pk_invoice), 0) from {{ this }})
{% endif %}
```

## Incremental models

Three properties of `xml2db` tables make incremental models simple:

* rows are only appended: `xml2db` never updates or deletes rows in its tables;
* keys increase: a new row gets a higher primary key than all existing rows of its table;
* a new row in a relationship table always belongs to a new parent row, inserted in the same load.

So an incremental model filters on the primary key of the table that defines its grain, and keeps the rows above the
highest key already in the model, as in `fct_invoice_lines` above.

Choose that table with deduplication in mind. An invoice found in several files is stored once, so a model driven by
`pk_invoice` holds each invoice once. To keep one row per file and invoice, as received, drive the model from the root
table, which gets one row per loaded file with new content:

``` sql title="models/marts/fct_received_invoices.sql"
{{ config(materialized='incremental') }}

select
    f.pk_invoices as pk_file,
    f.input_file_path,
    i.invoice_id,
    i.invoice_date
from {{ source('xml2db', 'invoices') }} as f
join {{ source('xml2db', 'invoices_invoice') }} as fi on fi.fk_invoices = f.pk_invoices
join {{ ref('stg_invoice') }} as i on i.pk_invoice = fi.fk_invoice
{% if is_incremental() %}
where f.pk_invoices > (select coalesce(max(pk_file), 0) from {{ this }})
{% endif %}
```

After loading `invoices_1.xml`, with invoices `INV-001` and `INV-002`, then `invoices_2.xml`, with `INV-002` and
`INV-003`:

=== "fct_invoice_lines"

    | pk_invoice | invoice_id | sku | quantity | amount |
    |-----------:|------------|-----|---------:|-------:|
    | 1          | INV-001    | X1  | 2        | 19.80  |
    | 1          | INV-001    | Y7  | 1        | 24.00  |
    | 2          | INV-002    | X1  | 2        | 19.80  |
    | 3          | INV-003    | Z9  | 5        | 17.50  |

=== "fct_received_invoices"

    | pk_file | input_file_path | invoice_id |
    |--------:|-----------------|------------|
    | 1       | invoices_1.xml  | INV-001    |
    | 1       | invoices_1.xml  | INV-002    |
    | 2       | invoices_2.xml  | INV-002    |
    | 2       | invoices_2.xml  | INV-003    |

Metadata columns are not part of the record hash: a file whose content was already loaded adds no row to the root
table, even under another name, and only the first file name is kept.

Do not filter on the key of a child table that can be shared: the line `X1` of `INV-002` reuses the row created for
`INV-001`, so its key is not new.

The filter relies on each load being complete when dbt runs. Run dbt after loads, merge files one at a time as
recommended in [Multiprocessing](how_it_works.md#multiprocessing), and keep the default single transaction of
`insert_into_target_tables`. `dbt run --full-refresh` rebuilds a model from all the raw data at any time.

## Corrected records

Deduplication compares whole records, so two versions of an invoice with the same identifier are two different
records. When a later file contains a corrected version of an invoice, it is stored as a new row, with a higher key.
A model can keep the latest version of each invoice:

``` sql title="models/marts/dim_invoice_latest.sql"
select invoice_id, invoice_date, customer_name, customer_country, pk_invoice
from (
    select
        *,
        row_number() over (partition by invoice_id order by pk_invoice desc) as version_rank
    from {{ ref('stg_invoice') }}
) as versions
where version_rank = 1
```

The order of the keys follows the order of the loads: load files in the order they were produced.

## Exporting from dbt

With `dbt-duckdb`, the `external` materialization writes a model to a Parquet file:

``` sql title="models/marts/invoice_lines_parquet.sql"
{{ config(materialized='external', location='invoice_lines.parquet') }}
select * from {{ ref('fct_invoice_lines') }}
```

See [Export to files, lakehouses and other databases](databases/export.md) for other targets.
