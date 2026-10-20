
CREATE TABLE `carrierId` (
	`pk_carrierId` INTEGER NOT NULL AUTO_INCREMENT, 
	vat VARCHAR(255), 
	registry VARCHAR(255), 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT `cx_pk_carrierId` PRIMARY KEY (`pk_carrierId`), 
	CONSTRAINT `carrierId_xml2db_record_hash` UNIQUE (xml2db_record_hash)
)


CREATE TABLE detail_1 (
	pk_detail_1 INTEGER NOT NULL AUTO_INCREMENT, 
	reference VARCHAR(255), 
	carrier VARCHAR(255), 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT cx_pk_detail_1 PRIMARY KEY (pk_detail_1), 
	CONSTRAINT detail_1_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE zip (
	pk_zip INTEGER NOT NULL AUTO_INCREMENT, 
	`codingSystem` VARCHAR(255), 
	state VARCHAR(255), 
	value VARCHAR(255), 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT cx_pk_zip PRIMARY KEY (pk_zip), 
	CONSTRAINT zip_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE `companyId` (
	`pk_companyId` INTEGER NOT NULL AUTO_INCREMENT, 
	ace VARCHAR(255), 
	bic VARCHAR(255), 
	lei VARCHAR(255), 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT `cx_pk_companyId` PRIMARY KEY (`pk_companyId`), 
	CONSTRAINT `companyId_xml2db_record_hash` UNIQUE (xml2db_record_hash)
)


CREATE TABLE catalog_ref (
	pk_catalog_ref INTEGER NOT NULL AUTO_INCREMENT, 
	id VARCHAR(255), 
	urn VARCHAR(1000), 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT cx_pk_catalog_ref PRIMARY KEY (pk_catalog_ref), 
	CONSTRAINT catalog_ref_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE detail (
	pk_detail INTEGER NOT NULL AUTO_INCREMENT, 
	weight DOUBLE, 
	unit VARCHAR(255), 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT cx_pk_detail PRIMARY KEY (pk_detail), 
	CONSTRAINT detail_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE intfeature_with_peculiarly_long_suffix_which_ove_5868736 (
	pk_intfeature_with_peculiarly_long_suffix_which__85b659b INTEGER NOT NULL AUTO_INCREMENT, 
	id VARCHAR(255), 
	value INTEGER, 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT cx_pk_intfeature_with_peculiarly_long_suffix_whi_ecb17be PRIMARY KEY (pk_intfeature_with_peculiarly_long_suffix_which__85b659b), 
	CONSTRAINT intfeature_with_peculia_0c087_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE stringfeature (
	pk_stringfeature INTEGER NOT NULL AUTO_INCREMENT, 
	id VARCHAR(255), 
	value VARCHAR(255), 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT cx_pk_stringfeature PRIMARY KEY (pk_stringfeature), 
	CONSTRAINT stringfeature_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE orderperson (
	pk_orderperson INTEGER NOT NULL AUTO_INCREMENT, 
	name_attr VARCHAR(255), 
	name VARCHAR(255), 
	address VARCHAR(255), 
	city VARCHAR(255), 
	fk_zip INTEGER, 
	country VARCHAR(255), 
	`phoneNumber` VARCHAR(4000), 
	`fk_companyId` INTEGER, 
	coordinates VARCHAR(255), 
	a_very_long_field_type_that_makes_col_name_excee_223ada0 VARCHAR(255), 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT cx_pk_orderperson PRIMARY KEY (pk_orderperson), 
	CONSTRAINT orderperson_xml2db_record_hash UNIQUE (xml2db_record_hash), 
	FOREIGN KEY(fk_zip) REFERENCES zip (pk_zip), 
	FOREIGN KEY(`fk_companyId`) REFERENCES `companyId` (`pk_companyId`)
)


CREATE TABLE features (
	pk_features INTEGER NOT NULL AUTO_INCREMENT, 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT cx_pk_features PRIMARY KEY (pk_features), 
	CONSTRAINT features_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE features_intfeature_with_peculiarly_long_suffix__4166a78 (
	fk_features INTEGER NOT NULL, 
	fk_intfeature_with_peculiarly_long_suffix_which__00590e9 INTEGER NOT NULL, 
	FOREIGN KEY(fk_features) REFERENCES features (pk_features), 
	FOREIGN KEY(fk_intfeature_with_peculiarly_long_suffix_which__00590e9) REFERENCES intfeature_with_peculiarly_long_suffix_which_ove_5868736 (pk_intfeature_with_peculiarly_long_suffix_which__85b659b)
)


CREATE TABLE features_stringfeature (
	fk_features INTEGER NOT NULL, 
	fk_stringfeature INTEGER NOT NULL, 
	FOREIGN KEY(fk_features) REFERENCES features (pk_features), 
	FOREIGN KEY(fk_stringfeature) REFERENCES stringfeature (pk_stringfeature)
)


CREATE TABLE delivery (
	pk_delivery INTEGER NOT NULL AUTO_INCREMENT, 
	from_fk_orderperson INTEGER, 
	to_fk_orderperson INTEGER, 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT cx_pk_delivery PRIMARY KEY (pk_delivery), 
	CONSTRAINT delivery_xml2db_record_hash UNIQUE (xml2db_record_hash), 
	FOREIGN KEY(from_fk_orderperson) REFERENCES orderperson (pk_orderperson), 
	FOREIGN KEY(to_fk_orderperson) REFERENCES orderperson (pk_orderperson)
)


CREATE TABLE product (
	pk_product INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(255), 
	version VARCHAR(255), 
	fk_features INTEGER, 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT cx_pk_product PRIMARY KEY (pk_product), 
	CONSTRAINT product_xml2db_record_hash UNIQUE (xml2db_record_hash), 
	FOREIGN KEY(fk_features) REFERENCES features (pk_features)
)


CREATE TABLE item (
	pk_item INTEGER NOT NULL AUTO_INCREMENT, 
	fk_product INTEGER, 
	note VARCHAR(255), 
	quantity INTEGER, 
	price DOUBLE, 
	currency VARCHAR(3), 
	fk_delivery INTEGER, 
	fk_catalog_ref INTEGER, 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT cx_pk_item PRIMARY KEY (pk_item), 
	CONSTRAINT item_xml2db_record_hash UNIQUE (xml2db_record_hash), 
	FOREIGN KEY(fk_product) REFERENCES product (pk_product), 
	FOREIGN KEY(fk_delivery) REFERENCES delivery (pk_delivery), 
	FOREIGN KEY(fk_catalog_ref) REFERENCES catalog_ref (pk_catalog_ref)
)


CREATE TABLE item_detail (
	fk_item INTEGER NOT NULL, 
	fk_detail INTEGER NOT NULL, 
	FOREIGN KEY(fk_item) REFERENCES item (pk_item), 
	FOREIGN KEY(fk_detail) REFERENCES detail (pk_detail)
)


CREATE TABLE shiporder (
	pk_shiporder INTEGER NOT NULL AUTO_INCREMENT, 
	orderid VARCHAR(255), 
	processed_at DATETIME, 
	fk_orderperson INTEGER, 
	shipto_fk_orderperson INTEGER, 
	`fk_carrierId` INTEGER, 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT cx_pk_shiporder PRIMARY KEY (pk_shiporder), 
	CONSTRAINT shiporder_xml2db_record_hash UNIQUE (xml2db_record_hash), 
	FOREIGN KEY(fk_orderperson) REFERENCES orderperson (pk_orderperson), 
	FOREIGN KEY(shipto_fk_orderperson) REFERENCES orderperson (pk_orderperson), 
	FOREIGN KEY(`fk_carrierId`) REFERENCES `carrierId` (`pk_carrierId`)
)


CREATE TABLE shiporder_item (
	fk_shiporder INTEGER NOT NULL, 
	fk_item INTEGER NOT NULL, 
	FOREIGN KEY(fk_shiporder) REFERENCES shiporder (pk_shiporder), 
	FOREIGN KEY(fk_item) REFERENCES item (pk_item)
)


CREATE TABLE shiporder_detail_detail_1 (
	fk_shiporder INTEGER NOT NULL, 
	fk_detail_1 INTEGER NOT NULL, 
	FOREIGN KEY(fk_shiporder) REFERENCES shiporder (pk_shiporder), 
	FOREIGN KEY(fk_detail_1) REFERENCES detail_1 (pk_detail_1)
)


CREATE TABLE orders (
	pk_orders INTEGER NOT NULL AUTO_INCREMENT, 
	batch_id VARCHAR(255), 
	version INTEGER, 
	input_file_path VARCHAR(256), 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT cx_pk_orders PRIMARY KEY (pk_orders), 
	CONSTRAINT orders_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE orders_shiporder (
	fk_orders INTEGER NOT NULL, 
	fk_shiporder INTEGER NOT NULL, 
	FOREIGN KEY(fk_orders) REFERENCES orders (pk_orders), 
	FOREIGN KEY(fk_shiporder) REFERENCES shiporder (pk_shiporder)
)

CREATE INDEX ix_features_intfeature_with_peculiarly_long_suffix__4166_6094 ON features_intfeature_with_peculiarly_long_suffix__4166a78 (fk_features)

CREATE INDEX ix_features_intfeature_with_peculiarly_long_suffix__4166_1469 ON features_intfeature_with_peculiarly_long_suffix__4166a78 (fk_intfeature_with_peculiarly_long_suffix_which__00590e9)

CREATE INDEX ix_features_stringfeature_fk_features ON features_stringfeature (fk_features)

CREATE INDEX ix_features_stringfeature_fk_stringfeature ON features_stringfeature (fk_stringfeature)

CREATE INDEX ix_item_detail_fk_detail ON item_detail (fk_detail)

CREATE INDEX ix_item_detail_fk_item ON item_detail (fk_item)

CREATE INDEX ix_shiporder_item_fk_item ON shiporder_item (fk_item)

CREATE INDEX ix_shiporder_item_fk_shiporder ON shiporder_item (fk_shiporder)

CREATE INDEX ix_shiporder_detail_detail_1_fk_detail_1 ON shiporder_detail_detail_1 (fk_detail_1)

CREATE INDEX ix_shiporder_detail_detail_1_fk_shiporder ON shiporder_detail_detail_1 (fk_shiporder)

CREATE INDEX ix_orders_shiporder_fk_orders ON orders_shiporder (fk_orders)

CREATE INDEX ix_orders_shiporder_fk_shiporder ON orders_shiporder (fk_shiporder)

