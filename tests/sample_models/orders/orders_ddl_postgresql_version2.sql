
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
	name VARCHAR(1000), 
	address VARCHAR(1000), 
	city VARCHAR(1000), 
	"zip_codingSystem" VARCHAR(1000), 
	zip_value VARCHAR(1000), 
	country VARCHAR(1000), 
	"phoneNumber" VARCHAR(8000), 
	"companyId_type" VARCHAR(3), 
	"companyId_value" VARCHAR(1000), 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_orderperson PRIMARY KEY (pk_orderperson), 
	CONSTRAINT orderperson_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE product (
	pk_product SERIAL NOT NULL, 
	name VARCHAR(1000), 
	version VARCHAR(1000), 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_product PRIMARY KEY (pk_product), 
	CONSTRAINT product_xml2db_record_hash UNIQUE (xml2db_record_hash)
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
	orderperson_name VARCHAR(1000), 
	orderperson_address VARCHAR(1000), 
	orderperson_city VARCHAR(1000), 
	"orderperson_zip_codingSystem" VARCHAR(1000), 
	orderperson_zip_value VARCHAR(1000), 
	orderperson_country VARCHAR(1000), 
	"orderperson_phoneNumber" VARCHAR(8000), 
	"orderperson_companyId_type" VARCHAR(3), 
	"orderperson_companyId_value" VARCHAR(1000), 
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

CREATE INDEX ix_shiporder_item_fk_item ON shiporder_item (fk_item)

CREATE INDEX ix_shiporder_item_fk_shiporder ON shiporder_item (fk_shiporder)

