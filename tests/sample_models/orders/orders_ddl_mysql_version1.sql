
CREATE TABLE orderperson (
	pk_orderperson INTEGER NOT NULL AUTO_INCREMENT, 
	name_attr VARCHAR(255), 
	name VARCHAR(255), 
	address VARCHAR(255), 
	city VARCHAR(255), 
	`zip_codingSystem` VARCHAR(255), 
	zip_state VARCHAR(255), 
	zip_value VARCHAR(255), 
	country VARCHAR(255), 
	`phoneNumber` VARCHAR(4000), 
	`companyId_ace` VARCHAR(255), 
	`companyId_bic` VARCHAR(255), 
	`companyId_lei` VARCHAR(255), 
	coordinates VARCHAR(255), 
	record_hash BINARY(16), 
	CONSTRAINT cx_pk_orderperson PRIMARY KEY (pk_orderperson), 
	CONSTRAINT orderperson_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE intfeature (
	pk_intfeature INTEGER NOT NULL AUTO_INCREMENT, 
	id VARCHAR(255), 
	value INTEGER, 
	record_hash BINARY(16), 
	CONSTRAINT cx_pk_intfeature PRIMARY KEY (pk_intfeature), 
	CONSTRAINT intfeature_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE stringfeature (
	pk_stringfeature INTEGER NOT NULL AUTO_INCREMENT, 
	id VARCHAR(255), 
	value VARCHAR(255), 
	record_hash BINARY(16), 
	CONSTRAINT cx_pk_stringfeature PRIMARY KEY (pk_stringfeature), 
	CONSTRAINT stringfeature_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE shiporder (
	pk_shiporder INTEGER NOT NULL AUTO_INCREMENT, 
	orderid VARCHAR(255), 
	processed_at DATETIME, 
	fk_orderperson INTEGER, 
	shipto_fk_orderperson INTEGER, 
	record_hash BINARY(16), 
	CONSTRAINT cx_pk_shiporder PRIMARY KEY (pk_shiporder), 
	CONSTRAINT shiporder_xml2db_record_hash UNIQUE (record_hash), 
	FOREIGN KEY(fk_orderperson) REFERENCES orderperson (pk_orderperson), 
	FOREIGN KEY(shipto_fk_orderperson) REFERENCES orderperson (pk_orderperson)
)


CREATE TABLE orders (
	pk_orders INTEGER NOT NULL AUTO_INCREMENT, 
	batch_id VARCHAR(255), 
	version INTEGER, 
	xml2db_processed_at DATETIME, 
	input_file_path VARCHAR(256), 
	record_hash BINARY(16), 
	CONSTRAINT cx_pk_orders PRIMARY KEY (pk_orders), 
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
	pk_item INTEGER NOT NULL AUTO_INCREMENT, 
	temp_pk_item INTEGER, 
	fk_parent_shiporder INTEGER, 
	xml2db_row_number INTEGER NOT NULL, 
	product_name VARCHAR(255), 
	product_version VARCHAR(255), 
	note VARCHAR(255), 
	quantity INTEGER, 
	price DOUBLE, 
	currency VARCHAR(3), 
	CONSTRAINT cx_pk_item PRIMARY KEY (pk_item), 
	FOREIGN KEY(fk_parent_shiporder) REFERENCES shiporder (pk_shiporder)
)


CREATE TABLE item_product_features_intfeature (
	fk_item INTEGER NOT NULL, 
	fk_intfeature INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(fk_item) REFERENCES item (pk_item), 
	FOREIGN KEY(fk_intfeature) REFERENCES intfeature (pk_intfeature)
)


CREATE TABLE item_product_features_stringfeature (
	fk_item INTEGER NOT NULL, 
	fk_stringfeature INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(fk_item) REFERENCES item (pk_item), 
	FOREIGN KEY(fk_stringfeature) REFERENCES stringfeature (pk_stringfeature)
)

CREATE INDEX ix_orders_shiporder_fk_orders ON orders_shiporder (fk_orders)

CREATE INDEX ix_orders_shiporder_fk_shiporder ON orders_shiporder (fk_shiporder)

CREATE INDEX ix_item_product_features_intfeature_fk_intfeature ON item_product_features_intfeature (fk_intfeature)

CREATE INDEX ix_item_product_features_intfeature_fk_item ON item_product_features_intfeature (fk_item)

CREATE INDEX ix_item_product_features_stringfeature_fk_item ON item_product_features_stringfeature (fk_item)

CREATE INDEX ix_item_product_features_stringfeature_fk_stringfeature ON item_product_features_stringfeature (fk_stringfeature)

