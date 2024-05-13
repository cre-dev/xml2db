
CREATE TABLE orders (
	pk_orders INTEGER NOT NULL IDENTITY, 
	batch_id VARCHAR(1000) NULL, 
	xml2db_input_file_path VARCHAR(256) NOT NULL, 
	xml2db_processed_at DATETIMEOFFSET NULL, 
	record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_orders PRIMARY KEY CLUSTERED (pk_orders), 
	CONSTRAINT orders_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE orderperson (
	pk_orderperson INTEGER NOT NULL IDENTITY, 
	name VARCHAR(1000) NULL, 
	address VARCHAR(1000) NULL, 
	city VARCHAR(1000) NULL, 
	[zip_codingSystem] VARCHAR(1000) NULL, 
	zip_value VARCHAR(1000) NULL, 
	country VARCHAR(1000) NULL, 
	[phoneNumber] VARCHAR(8000) NULL, 
	[companyId_type] CHAR(3) NULL, 
	[companyId_value] VARCHAR(1000) NULL, 
	record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_orderperson PRIMARY KEY CLUSTERED (pk_orderperson), 
	CONSTRAINT orderperson_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE product (
	pk_product INTEGER NOT NULL IDENTITY, 
	name VARCHAR(1000) NULL, 
	version VARCHAR(1000) NULL, 
	record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_product PRIMARY KEY CLUSTERED (pk_product), 
	CONSTRAINT product_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE item (
	pk_item INTEGER NOT NULL IDENTITY, 
	fk_product INTEGER NULL, 
	note VARCHAR(1000) NULL, 
	quantity INTEGER NULL, 
	price DOUBLE PRECISION NULL, 
	record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_item PRIMARY KEY CLUSTERED (pk_item), 
	CONSTRAINT item_xml2db_record_hash UNIQUE (record_hash), 
	FOREIGN KEY(fk_product) REFERENCES product (pk_product)
)


CREATE TABLE shiporder (
	pk_shiporder INTEGER NOT NULL IDENTITY, 
	temp_pk_shiporder INTEGER NULL, 
	fk_parent_orders INTEGER NULL, 
	orderid VARCHAR(1000) NULL, 
	processed_at DATETIMEOFFSET NULL, 
	orderperson_name VARCHAR(1000) NULL, 
	orderperson_address VARCHAR(1000) NULL, 
	orderperson_city VARCHAR(1000) NULL, 
	[orderperson_zip_codingSystem] VARCHAR(1000) NULL, 
	orderperson_zip_value VARCHAR(1000) NULL, 
	orderperson_country VARCHAR(1000) NULL, 
	[orderperson_phoneNumber] VARCHAR(8000) NULL, 
	[orderperson_companyId_type] CHAR(3) NULL, 
	[orderperson_companyId_value] VARCHAR(1000) NULL, 
	shipto_fk_orderperson INTEGER NULL, 
	CONSTRAINT cx_pk_shiporder PRIMARY KEY CLUSTERED (pk_shiporder), 
	FOREIGN KEY(fk_parent_orders) REFERENCES orders (pk_orders), 
	FOREIGN KEY(shipto_fk_orderperson) REFERENCES orderperson (pk_orderperson)
)


CREATE TABLE shiporder_item (
	fk_shiporder INTEGER NOT NULL, 
	fk_item INTEGER NOT NULL, 
	FOREIGN KEY(fk_shiporder) REFERENCES shiporder (pk_shiporder), 
	FOREIGN KEY(fk_item) REFERENCES item (pk_item)
)

CREATE INDEX ix_item_fk_product ON item (fk_product)

CREATE INDEX ix_shiporder_fk_parent_orders ON shiporder (fk_parent_orders)

CREATE INDEX ix_shiporder_shipto_fk_orderperson ON shiporder (shipto_fk_orderperson)

CREATE INDEX ix_shiporder_item_fk_item ON shiporder_item (fk_item)

