
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
	record_hash BYTEA, 
	CONSTRAINT cx_pk_orderperson PRIMARY KEY (pk_orderperson), 
	CONSTRAINT orderperson_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE item (
	pk_item SERIAL NOT NULL, 
	product_name VARCHAR(1000), 
	product_version VARCHAR(1000), 
	note VARCHAR(1000), 
	quantity INTEGER, 
	price DOUBLE PRECISION, 
	currency VARCHAR(3), 
	record_hash BYTEA, 
	CONSTRAINT cx_pk_item PRIMARY KEY (pk_item), 
	CONSTRAINT item_xml2db_record_hash UNIQUE (record_hash)
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


CREATE TABLE shiporder_item (
	fk_shiporder INTEGER NOT NULL, 
	fk_item INTEGER NOT NULL, 
	FOREIGN KEY(fk_shiporder) REFERENCES shiporder (pk_shiporder), 
	FOREIGN KEY(fk_item) REFERENCES item (pk_item)
)


CREATE TABLE orders (
	pk_orders SERIAL NOT NULL, 
	batch_id VARCHAR(1000), 
	version INTEGER, 
	input_file_path VARCHAR(256), 
	record_hash BYTEA, 
	CONSTRAINT cx_pk_orders PRIMARY KEY (pk_orders), 
	CONSTRAINT orders_xml2db_record_hash UNIQUE (record_hash)
)


CREATE TABLE orders_shiporder (
	fk_orders INTEGER NOT NULL, 
	fk_shiporder INTEGER NOT NULL, 
	FOREIGN KEY(fk_orders) REFERENCES orders (pk_orders), 
	FOREIGN KEY(fk_shiporder) REFERENCES shiporder (pk_shiporder)
)

CREATE INDEX ix_shiporder_item_fk_item ON shiporder_item (fk_item)

CREATE INDEX ix_shiporder_item_fk_shiporder ON shiporder_item (fk_shiporder)

CREATE INDEX ix_orders_shiporder_fk_orders ON orders_shiporder (fk_orders)

CREATE INDEX ix_orders_shiporder_fk_shiporder ON orders_shiporder (fk_shiporder)

