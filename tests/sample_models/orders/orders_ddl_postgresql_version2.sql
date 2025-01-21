
CREATE TABLE orders (
	pk_orders SERIAL NOT NULL, 
	batch_id VARCHAR(1000), 
	version INTEGER, 
	input_file_path VARCHAR(256), 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_orders PRIMARY KEY (pk_orders), 
	CONSTRAINT orders_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


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
	"companyId_type" VARCHAR(3), 
	"companyId_value" VARCHAR(1000), 
	coordinates VARCHAR(1000), 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_orderperson PRIMARY KEY (pk_orderperson), 
	CONSTRAINT orderperson_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE intfeature (
	pk_intfeature SERIAL NOT NULL, 
	id VARCHAR(1000), 
	value INTEGER, 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_intfeature PRIMARY KEY (pk_intfeature), 
	CONSTRAINT intfeature_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE stringfeature (
	pk_stringfeature SERIAL NOT NULL, 
	id VARCHAR(1000), 
	value VARCHAR(1000), 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_stringfeature PRIMARY KEY (pk_stringfeature), 
	CONSTRAINT stringfeature_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE product (
	pk_product SERIAL NOT NULL, 
	name VARCHAR(1000), 
	version VARCHAR(1000), 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_product PRIMARY KEY (pk_product), 
	CONSTRAINT product_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE product_features_intfeature (
	fk_product INTEGER NOT NULL, 
	fk_intfeature INTEGER NOT NULL, 
	FOREIGN KEY(fk_product) REFERENCES product (pk_product), 
	FOREIGN KEY(fk_intfeature) REFERENCES intfeature (pk_intfeature)
)


CREATE TABLE product_features_stringfeature (
	fk_product INTEGER NOT NULL, 
	fk_stringfeature INTEGER NOT NULL, 
	FOREIGN KEY(fk_product) REFERENCES product (pk_product), 
	FOREIGN KEY(fk_stringfeature) REFERENCES stringfeature (pk_stringfeature)
)


CREATE TABLE item (
	pk_item SERIAL NOT NULL, 
	fk_product INTEGER, 
	note VARCHAR(1000), 
	quantity INTEGER, 
	price DOUBLE PRECISION, 
	currency VARCHAR(3), 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_item PRIMARY KEY (pk_item), 
	CONSTRAINT item_xml2db_record_hash UNIQUE (xml2db_record_hash), 
	FOREIGN KEY(fk_product) REFERENCES product (pk_product)
)


CREATE TABLE shiporder (
	pk_shiporder SERIAL NOT NULL, 
	temp_pk_shiporder INTEGER, 
	fk_parent_orders INTEGER, 
	orderid VARCHAR(1000), 
	processed_at TIMESTAMP WITH TIME ZONE, 
	orderperson_name_attr VARCHAR(1000), 
	orderperson_name VARCHAR(1000), 
	orderperson_address VARCHAR(1000), 
	orderperson_city VARCHAR(1000), 
	"orderperson_zip_codingSystem" VARCHAR(1000), 
	orderperson_zip_value VARCHAR(1000), 
	orderperson_country VARCHAR(1000), 
	"orderperson_phoneNumber" VARCHAR(8000), 
	"orderperson_companyId_type" VARCHAR(3), 
	"orderperson_companyId_value" VARCHAR(1000), 
	orderperson_coordinates VARCHAR(1000), 
	shipto_fk_orderperson INTEGER, 
	CONSTRAINT cx_pk_shiporder PRIMARY KEY (pk_shiporder), 
	FOREIGN KEY(fk_parent_orders) REFERENCES orders (pk_orders), 
	FOREIGN KEY(shipto_fk_orderperson) REFERENCES orderperson (pk_orderperson)
)


CREATE TABLE shiporder_item (
	fk_shiporder INTEGER NOT NULL, 
	fk_item INTEGER NOT NULL, 
	FOREIGN KEY(fk_shiporder) REFERENCES shiporder (pk_shiporder), 
	FOREIGN KEY(fk_item) REFERENCES item (pk_item)
)

CREATE INDEX ix_product_features_intfeature_fk_intfeature ON product_features_intfeature (fk_intfeature)

CREATE INDEX ix_product_features_intfeature_fk_product ON product_features_intfeature (fk_product)

CREATE INDEX ix_product_features_stringfeature_fk_product ON product_features_stringfeature (fk_product)

CREATE INDEX ix_product_features_stringfeature_fk_stringfeature ON product_features_stringfeature (fk_stringfeature)

CREATE INDEX ix_shiporder_item_fk_item ON shiporder_item (fk_item)

CREATE INDEX ix_shiporder_item_fk_shiporder ON shiporder_item (fk_shiporder)

