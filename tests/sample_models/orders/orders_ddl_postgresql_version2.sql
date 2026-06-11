
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
	zip_state VARCHAR(1000), 
	zip_value VARCHAR(1000), 
	country VARCHAR(1000), 
	"phoneNumber" VARCHAR(8000), 
	"companyId_type" VARCHAR(3), 
	"companyId_value" VARCHAR(1000), 
	coordinates VARCHAR(1000), 
	a_very_long_field_type_that_makes_col_name_exceeds_max__223ada0 VARCHAR(1000), 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_orderperson PRIMARY KEY (pk_orderperson), 
	CONSTRAINT orderperson_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE intfeature_with_peculiarly_long_suffix_which_overflow_m_5868736 (
	pk_intfeature_with_peculiarly_long_suffix_which_overflo_85b659b SERIAL NOT NULL, 
	id VARCHAR(1000), 
	value INTEGER, 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_intfeature_with_peculiarly_long_suffix_which_over_ecb17be PRIMARY KEY (pk_intfeature_with_peculiarly_long_suffix_which_overflo_85b659b), 
	CONSTRAINT intfeature_with_peculia_0c087_xml2db_record_hash UNIQUE (xml2db_record_hash)
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


CREATE TABLE product_features_intfeature_with_peculiarly_long_suffix_82a4847 (
	fk_product INTEGER NOT NULL, 
	fk_intfeature_with_peculiarly_long_suffix_which_overflo_00590e9 INTEGER NOT NULL, 
	FOREIGN KEY(fk_product) REFERENCES product (pk_product), 
	FOREIGN KEY(fk_intfeature_with_peculiarly_long_suffix_which_overflo_00590e9) REFERENCES intfeature_with_peculiarly_long_suffix_which_overflow_m_5868736 (pk_intfeature_with_peculiarly_long_suffix_which_overflo_85b659b)
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
	delivery_from_fk_orderperson INTEGER, 
	delivery_to_fk_orderperson INTEGER, 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_item PRIMARY KEY (pk_item), 
	CONSTRAINT item_xml2db_record_hash UNIQUE (xml2db_record_hash), 
	FOREIGN KEY(fk_product) REFERENCES product (pk_product), 
	FOREIGN KEY(delivery_from_fk_orderperson) REFERENCES orderperson (pk_orderperson), 
	FOREIGN KEY(delivery_to_fk_orderperson) REFERENCES orderperson (pk_orderperson)
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
	orderperson_zip_state VARCHAR(1000), 
	orderperson_zip_value VARCHAR(1000), 
	orderperson_country VARCHAR(1000), 
	"orderperson_phoneNumber" VARCHAR(8000), 
	"orderperson_companyId_type" VARCHAR(3), 
	"orderperson_companyId_value" VARCHAR(1000), 
	orderperson_coordinates VARCHAR(1000), 
	orderperson_a_very_long_field_type_that_makes_col_name__ee3c2ee VARCHAR(1000), 
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

CREATE INDEX ix_product_features_intfeature_with_peculiarly_long_suf_63f4 ON product_features_intfeature_with_peculiarly_long_suffix_82a4847 (fk_intfeature_with_peculiarly_long_suffix_which_overflo_00590e9)

CREATE INDEX ix_product_features_intfeature_with_peculiarly_long_suf_0375 ON product_features_intfeature_with_peculiarly_long_suffix_82a4847 (fk_product)

CREATE INDEX ix_product_features_stringfeature_fk_product ON product_features_stringfeature (fk_product)

CREATE INDEX ix_product_features_stringfeature_fk_stringfeature ON product_features_stringfeature (fk_stringfeature)

CREATE INDEX ix_shiporder_item_fk_item ON shiporder_item (fk_item)

CREATE INDEX ix_shiporder_item_fk_shiporder ON shiporder_item (fk_shiporder)

