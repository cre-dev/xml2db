
CREATE TABLE orderperson (
	pk_orderperson INTEGER NOT NULL IDENTITY, 
	name_attr VARCHAR(1000) NULL, 
	name VARCHAR(1000) NULL, 
	address VARCHAR(1000) NULL, 
	city VARCHAR(1000) NULL, 
	[zip_codingSystem] VARCHAR(1000) NULL, 
	zip_value VARCHAR(1000) NULL, 
	country VARCHAR(1000) NULL, 
	[phoneNumber] VARCHAR(8000) NULL, 
	[companyId_type] CHAR(3) NULL, 
	[companyId_value] VARCHAR(1000) NULL, 
	coordinates VARCHAR(1000) NULL, 
	record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_orderperson PRIMARY KEY CLUSTERED (pk_orderperson), 
	CONSTRAINT orderperson_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE item (
	pk_item INTEGER NOT NULL IDENTITY, 
	product_name VARCHAR(1000) NULL, 
	product_version VARCHAR(1000) NULL, 
	note VARCHAR(1000) NULL, 
	quantity INTEGER NULL, 
	price DOUBLE PRECISION NULL, 
	currency CHAR(3) NULL, 
	record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_item PRIMARY KEY CLUSTERED (pk_item), 
	CONSTRAINT item_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE shiporder (
	pk_shiporder INTEGER NOT NULL IDENTITY, 
	orderid VARCHAR(1000) NULL, 
	processed_at DATETIMEOFFSET NULL, 
	fk_orderperson INTEGER NULL, 
	shipto_fk_orderperson INTEGER NULL, 
	record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_shiporder PRIMARY KEY CLUSTERED (pk_shiporder), 
	CONSTRAINT shiporder_xml2db_record_hash UNIQUE (record_hash), 
	FOREIGN KEY(fk_orderperson) REFERENCES orderperson (pk_orderperson), 
	FOREIGN KEY(shipto_fk_orderperson) REFERENCES orderperson (pk_orderperson)
)


CREATE TABLE shiporder_item (
	fk_shiporder INTEGER NOT NULL, 
	fk_item INTEGER NOT NULL, 
	FOREIGN KEY(fk_shiporder) REFERENCES shiporder (pk_shiporder), 
	FOREIGN KEY(fk_item) REFERENCES item (pk_item)
)


CREATE TABLE orders (
	pk_orders INTEGER NOT NULL IDENTITY, 
	batch_id VARCHAR(1000) NULL, 
	version INTEGER NULL, 
	input_file_path VARCHAR(256) NULL, 
	record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_orders PRIMARY KEY CLUSTERED (pk_orders), 
	CONSTRAINT orders_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE orders_shiporder (
	fk_orders INTEGER NOT NULL, 
	fk_shiporder INTEGER NOT NULL, 
	FOREIGN KEY(fk_orders) REFERENCES orders (pk_orders), 
	FOREIGN KEY(fk_shiporder) REFERENCES shiporder (pk_shiporder)
)

CREATE CLUSTERED INDEX ix_fk_shiporder_item ON shiporder_item (fk_shiporder, fk_item)

CREATE INDEX ix_shiporder_item_fk_item ON shiporder_item (fk_item)

CREATE CLUSTERED INDEX ix_fk_orders_shiporder ON orders_shiporder (fk_orders, fk_shiporder)

CREATE INDEX ix_orders_shiporder_fk_shiporder ON orders_shiporder (fk_shiporder)

