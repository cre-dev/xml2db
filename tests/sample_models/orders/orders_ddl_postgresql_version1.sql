
CREATE TABLE orderperson (
	pk_orderperson SERIAL NOT NULL, 
	name_attr VARCHAR(1000), 
	name VARCHAR(1000), 
	address VARCHAR(1000), 
	city VARCHAR(1000), 
	"zip_codingSystem" VARCHAR(1000), 
	zip_value VARCHAR(1000), 
	country VARCHAR(1000), 
	"phoneNumber" VARCHAR(8000), 
	"companyId_ace" VARCHAR(1000), 
	"companyId_bic" VARCHAR(1000), 
	"companyId_lei" VARCHAR(1000), 
	coordinates VARCHAR(1000), 
	record_hash BYTEA, 
	CONSTRAINT cx_pk_orderperson PRIMARY KEY (pk_orderperson), 
	CONSTRAINT orderperson_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE intfeature (
	pk_intfeature SERIAL NOT NULL, 
	id VARCHAR(1000), 
	value INTEGER, 
	record_hash BYTEA, 
	CONSTRAINT cx_pk_intfeature PRIMARY KEY (pk_intfeature), 
	CONSTRAINT intfeature_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE stringfeature (
	pk_stringfeature SERIAL NOT NULL, 
	id VARCHAR(1000), 
	value VARCHAR(1000), 
	record_hash BYTEA, 
	CONSTRAINT cx_pk_stringfeature PRIMARY KEY (pk_stringfeature), 
	CONSTRAINT stringfeature_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE shiporder (
	pk_shiporder SERIAL NOT NULL, 
	orderid VARCHAR(1000), 
	processed_at TIMESTAMP WITH TIME ZONE, 
	fk_orderperson INTEGER, 
	shipto_fk_orderperson INTEGER, 
	record_hash BYTEA, 
	CONSTRAINT cx_pk_shiporder PRIMARY KEY (pk_shiporder), 
	CONSTRAINT shiporder_xml2db_record_hash UNIQUE (record_hash), 
	FOREIGN KEY(fk_orderperson) REFERENCES orderperson (pk_orderperson), 
	FOREIGN KEY(shipto_fk_orderperson) REFERENCES orderperson (pk_orderperson)
)


CREATE TABLE orders (
	pk_orders SERIAL NOT NULL, 
	batch_id VARCHAR(1000), 
	version INTEGER, 
	xml2db_processed_at TIMESTAMP WITH TIME ZONE, 
	input_file_path VARCHAR(256), 
	record_hash BYTEA, 
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
	pk_item SERIAL NOT NULL, 
	temp_pk_item INTEGER, 
	fk_parent_shiporder INTEGER, 
	xml2db_row_number INTEGER NOT NULL, 
	product_name VARCHAR(1000), 
	product_version VARCHAR(1000), 
	note VARCHAR(1000), 
	quantity INTEGER, 
	price DOUBLE PRECISION, 
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

