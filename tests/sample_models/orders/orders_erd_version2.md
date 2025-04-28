```mermaid
erDiagram
    shiporder ||--o| orderperson : "shipto"
    shiporder ||--|{ item : "item*"
    shiporder {
        string orderid
        dateTime processed_at
        string orderperson_name_attr
        string orderperson_name
        string orderperson_address
        string orderperson_city
        string orderperson_zip_codingSystem
        string orderperson_zip_state
        string orderperson_zip_value
        string orderperson_country
        string-N orderperson_phoneNumber
        string orderperson_companyId_type
        string orderperson_companyId_value
        string orderperson_coordinates
    }
    item ||--|| product : "product"
    item {
        string note
        integer quantity
        decimal price
        string currency
    }
    product ||--o{ intfeature : "features_intfeature*"
    product ||--o{ stringfeature : "features_stringfeature*"
    product {
        string name
        string version
    }
    stringfeature {
        string id
        string value
    }
    intfeature {
        string id
        integer value
    }
    orderperson {
        string name_attr
        string name
        string address
        string city
        string zip_codingSystem
        string zip_state
        string zip_value
        string country
        string-N phoneNumber
        string companyId_type
        string companyId_value
        string coordinates
    }
    orders ||--o{ shiporder : "shiporder"
    orders {
        string batch_id
        int version
    }
```