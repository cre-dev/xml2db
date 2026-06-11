
CREATE TABLE orderperson (
	pk_orderperson INTEGER NOT NULL IDENTITY, 
	name_attr VARCHAR(1000) NULL, 
	name VARCHAR(1000) NULL, 
	address VARCHAR(1000) NULL, 
	city VARCHAR(1000) NULL, 
	[zip_codingSystem] VARCHAR(1000) NULL, 
	zip_state VARCHAR(1000) NULL, 
	zip_value VARCHAR(1000) NULL, 
	country VARCHAR(1000) NULL, 
	[phoneNumber] VARCHAR(8000) NULL, 
	[companyId_ace] VARCHAR(1000) NULL, 
	[companyId_bic] VARCHAR(1000) NULL, 
	[companyId_lei] VARCHAR(1000) NULL, 
	coordinates VARCHAR(1000) NULL, 
	a_very_long_field_type_that_makes_col_name_exceeds_max_identifier_length VARCHAR(1000) NULL, 
	record_hash BINARY(16) NULL, 
	CONSTRAINT cx_pk_orderperson PRIMARY KEY CLUSTERED (pk_orderperson), 
	CONSTRAINT orderperson_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE intfeature_with_peculiarly_long_suffix_which_overflow_max_length (
	pk_intfeature_with_peculiarly_long_suffix_which_overflow_max_length INTEGER NOT NULL IDENTITY, 
	id VARCHAR(1000) NULL, 
	value INTEGER NULL, 
	record_hash BINARY(16) NULL, 
	CONSTRAINT cx_pk_intfeature_with_peculiarly_long_suffix_which_overflow_max_length PRIMARY KEY CLUSTERED (pk_intfeature_with_peculiarly_long_suffix_which_overflow_max_length), 
	CONSTRAINT intfeature_with_peculia_0c087_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE stringfeature (
	pk_stringfeature INTEGER NOT NULL IDENTITY, 
	id VARCHAR(1000) NULL, 
	value VARCHAR(1000) NULL, 
	record_hash BINARY(16) NULL, 
	CONSTRAINT cx_pk_stringfeature PRIMARY KEY CLUSTERED (pk_stringfeature), 
	CONSTRAINT stringfeature_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE shiporder (
	pk_shiporder INTEGER NOT NULL IDENTITY, 
	orderid VARCHAR(1000) NULL, 
	processed_at DATETIMEOFFSET NULL, 
	fk_orderperson INTEGER NULL, 
	shipto_fk_orderperson INTEGER NULL, 
	record_hash BINARY(16) NULL, 
	CONSTRAINT cx_pk_shiporder PRIMARY KEY CLUSTERED (pk_shiporder), 
	CONSTRAINT shiporder_xml2db_record_hash UNIQUE (record_hash), 
	FOREIGN KEY(fk_orderperson) REFERENCES orderperson (pk_orderperson), 
	FOREIGN KEY(shipto_fk_orderperson) REFERENCES orderperson (pk_orderperson)
)


CREATE TABLE orders (
	pk_orders INTEGER NOT NULL IDENTITY, 
	batch_id VARCHAR(1000) NULL, 
	version INTEGER NULL, 
	xml2db_processed_at DATETIMEOFFSET NULL, 
	input_file_path VARCHAR(256) NULL, 
	record_hash BINARY(16) NULL, 
	CONSTRAINT cx_pk_orders PRIMARY KEY CLUSTERED (pk_orders), 
	CONSTRAINT orders_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE orders_shiporder (
	fk_orders INTEGER NOT NULL, 
	fk_shiporder INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(fk_orders) REFERENCES orders (pk_orders), 
	FOREIGN KEY(fk_shiporder) REFERENCES shiporder (pk_shiporder)
)


CREATE TABLE item (
	pk_item INTEGER NOT NULL IDENTITY, 
	temp_pk_item INTEGER NULL, 
	fk_parent_shiporder INTEGER NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	product_name VARCHAR(1000) NULL, 
	product_version VARCHAR(1000) NULL, 
	note VARCHAR(1000) NULL, 
	quantity INTEGER NULL, 
	price DOUBLE PRECISION NULL, 
	currency CHAR(3) NULL, 
	delivery_from_fk_orderperson INTEGER NULL, 
	delivery_to_fk_orderperson INTEGER NULL, 
	CONSTRAINT cx_pk_item PRIMARY KEY CLUSTERED (pk_item), 
	FOREIGN KEY(fk_parent_shiporder) REFERENCES shiporder (pk_shiporder), 
	FOREIGN KEY(delivery_from_fk_orderperson) REFERENCES orderperson (pk_orderperson), 
	FOREIGN KEY(delivery_to_fk_orderperson) REFERENCES orderperson (pk_orderperson)
)


CREATE TABLE item_product_features_intfeature_with_peculiarly_long_suffix_which_overflow_max_length (
	fk_item INTEGER NOT NULL, 
	fk_intfeature_with_peculiarly_long_suffix_which_overflow_max_length INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(fk_item) REFERENCES item (pk_item), 
	FOREIGN KEY(fk_intfeature_with_peculiarly_long_suffix_which_overflow_max_length) REFERENCES intfeature_with_peculiarly_long_suffix_which_overflow_max_length (pk_intfeature_with_peculiarly_long_suffix_which_overflow_max_length)
)


CREATE TABLE item_product_features_stringfeature (
	fk_item INTEGER NOT NULL, 
	fk_stringfeature INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(fk_item) REFERENCES item (pk_item), 
	FOREIGN KEY(fk_stringfeature) REFERENCES stringfeature (pk_stringfeature)
)

CREATE CLUSTERED INDEX ix_fk_orders_shiporder ON orders_shiporder (fk_orders, fk_shiporder)

CREATE INDEX ix_orders_shiporder_fk_shiporder ON orders_shiporder (fk_shiporder)

CREATE CLUSTERED INDEX ix_fk_item_product_features_intfeature_with_peculiarly_long_suffix_which_overflow_max_length ON item_product_features_intfeature_with_peculiarly_long_suffix_which_overflow_max_length (fk_item, fk_intfeature_with_peculiarly_long_suffix_which_overflow_max_length)

CREATE INDEX ix_item_product_features_intfeature_with_peculiarly_long_suffix_which_overflow_max_length_fk_intfeature_with_peculiarly__7aff ON item_product_features_intfeature_with_peculiarly_long_suffix_which_overflow_max_length (fk_intfeature_with_peculiarly_long_suffix_which_overflow_max_length)

CREATE CLUSTERED INDEX ix_fk_item_product_features_stringfeature ON item_product_features_stringfeature (fk_item, fk_stringfeature)

CREATE INDEX ix_item_product_features_stringfeature_fk_stringfeature ON item_product_features_stringfeature (fk_stringfeature)

