
CREATE TABLE [carrierId] (
	[pk_carrierId] INTEGER NOT NULL IDENTITY, 
	vat VARCHAR(1000) NULL, 
	registry VARCHAR(1000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT [cx_pk_carrierId] PRIMARY KEY CLUSTERED ([pk_carrierId]), 
	CONSTRAINT [carrierId_xml2db_record_hash] UNIQUE (xml2db_record_hash)
)


CREATE TABLE detail_1 (
	pk_detail_1 INTEGER NOT NULL IDENTITY, 
	reference VARCHAR(1000) NULL, 
	carrier VARCHAR(1000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_detail_1 PRIMARY KEY CLUSTERED (pk_detail_1), 
	CONSTRAINT detail_1_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE zip (
	pk_zip INTEGER NOT NULL IDENTITY, 
	[codingSystem] VARCHAR(1000) NULL, 
	state VARCHAR(1000) NULL, 
	value VARCHAR(1000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_zip PRIMARY KEY CLUSTERED (pk_zip), 
	CONSTRAINT zip_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE [companyId] (
	[pk_companyId] INTEGER NOT NULL IDENTITY, 
	type CHAR(3) NULL, 
	value VARCHAR(1000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT [cx_pk_companyId] PRIMARY KEY CLUSTERED ([pk_companyId]), 
	CONSTRAINT [companyId_xml2db_record_hash] UNIQUE (xml2db_record_hash)
)


CREATE TABLE catalog_ref (
	pk_catalog_ref INTEGER NOT NULL IDENTITY, 
	id VARCHAR(1000) NULL, 
	urn VARCHAR(1000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_catalog_ref PRIMARY KEY CLUSTERED (pk_catalog_ref), 
	CONSTRAINT catalog_ref_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE detail (
	pk_detail INTEGER NOT NULL IDENTITY, 
	weight DOUBLE PRECISION NULL, 
	unit VARCHAR(1000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_detail PRIMARY KEY CLUSTERED (pk_detail), 
	CONSTRAINT detail_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE intfeature_with_peculiarly_long_suffix_which_overflow_max_length (
	pk_intfeature_with_peculiarly_long_suffix_which_overflow_max_length INTEGER NOT NULL IDENTITY, 
	id VARCHAR(1000) NULL, 
	value INTEGER NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_intfeature_with_peculiarly_long_suffix_which_overflow_max_length PRIMARY KEY CLUSTERED (pk_intfeature_with_peculiarly_long_suffix_which_overflow_max_length), 
	CONSTRAINT intfeature_with_peculia_0c087_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE stringfeature (
	pk_stringfeature INTEGER NOT NULL IDENTITY, 
	id VARCHAR(1000) NULL, 
	value VARCHAR(1000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_stringfeature PRIMARY KEY CLUSTERED (pk_stringfeature), 
	CONSTRAINT stringfeature_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE orderperson (
	pk_orderperson INTEGER NOT NULL IDENTITY, 
	name_attr VARCHAR(1000) NULL, 
	name VARCHAR(1000) NULL, 
	address VARCHAR(1000) NULL, 
	city VARCHAR(1000) NULL, 
	fk_zip INTEGER NULL, 
	country VARCHAR(1000) NULL, 
	[phoneNumber] VARCHAR(8000) NULL, 
	[fk_companyId] INTEGER NULL, 
	coordinates VARCHAR(1000) NULL, 
	a_very_long_field_type_that_makes_col_name_exceeds_max_identifier_length VARCHAR(1000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_orderperson PRIMARY KEY CLUSTERED (pk_orderperson), 
	CONSTRAINT orderperson_xml2db_record_hash UNIQUE (xml2db_record_hash), 
	FOREIGN KEY(fk_zip) REFERENCES zip (pk_zip), 
	FOREIGN KEY([fk_companyId]) REFERENCES [companyId] ([pk_companyId])
)


CREATE TABLE features (
	pk_features INTEGER NOT NULL IDENTITY, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_features PRIMARY KEY CLUSTERED (pk_features), 
	CONSTRAINT features_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE features_intfeature_with_peculiarly_long_suffix_which_overflow_max_length (
	fk_features INTEGER NOT NULL, 
	fk_intfeature_with_peculiarly_long_suffix_which_overflow_max_length INTEGER NOT NULL, 
	FOREIGN KEY(fk_features) REFERENCES features (pk_features), 
	FOREIGN KEY(fk_intfeature_with_peculiarly_long_suffix_which_overflow_max_length) REFERENCES intfeature_with_peculiarly_long_suffix_which_overflow_max_length (pk_intfeature_with_peculiarly_long_suffix_which_overflow_max_length)
)


CREATE TABLE features_stringfeature (
	fk_features INTEGER NOT NULL, 
	fk_stringfeature INTEGER NOT NULL, 
	FOREIGN KEY(fk_features) REFERENCES features (pk_features), 
	FOREIGN KEY(fk_stringfeature) REFERENCES stringfeature (pk_stringfeature)
)


CREATE TABLE delivery (
	pk_delivery INTEGER NOT NULL IDENTITY, 
	from_fk_orderperson INTEGER NULL, 
	to_fk_orderperson INTEGER NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_delivery PRIMARY KEY CLUSTERED (pk_delivery), 
	CONSTRAINT delivery_xml2db_record_hash UNIQUE (xml2db_record_hash), 
	FOREIGN KEY(from_fk_orderperson) REFERENCES orderperson (pk_orderperson), 
	FOREIGN KEY(to_fk_orderperson) REFERENCES orderperson (pk_orderperson)
)


CREATE TABLE product (
	pk_product INTEGER NOT NULL IDENTITY, 
	name VARCHAR(1000) NULL, 
	version VARCHAR(1000) NULL, 
	fk_features INTEGER NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_product PRIMARY KEY CLUSTERED (pk_product), 
	CONSTRAINT product_xml2db_record_hash UNIQUE (xml2db_record_hash), 
	FOREIGN KEY(fk_features) REFERENCES features (pk_features)
)


CREATE TABLE item (
	pk_item INTEGER NOT NULL IDENTITY, 
	fk_product INTEGER NULL, 
	note VARCHAR(1000) NULL, 
	quantity INTEGER NULL, 
	price DOUBLE PRECISION NULL, 
	currency CHAR(3) NULL, 
	fk_delivery INTEGER NULL, 
	fk_catalog_ref INTEGER NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_item PRIMARY KEY CLUSTERED (pk_item), 
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
	pk_shiporder INTEGER NOT NULL IDENTITY, 
	orderid VARCHAR(1000) NULL, 
	processed_at DATETIMEOFFSET NULL, 
	fk_orderperson INTEGER NULL, 
	shipto_fk_orderperson INTEGER NULL, 
	[fk_carrierId] INTEGER NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_shiporder PRIMARY KEY CLUSTERED (pk_shiporder), 
	CONSTRAINT shiporder_xml2db_record_hash UNIQUE (xml2db_record_hash), 
	FOREIGN KEY(fk_orderperson) REFERENCES orderperson (pk_orderperson), 
	FOREIGN KEY(shipto_fk_orderperson) REFERENCES orderperson (pk_orderperson), 
	FOREIGN KEY([fk_carrierId]) REFERENCES [carrierId] ([pk_carrierId])
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
	pk_orders INTEGER NOT NULL IDENTITY, 
	batch_id VARCHAR(1000) NULL, 
	version INTEGER NULL, 
	input_file_path VARCHAR(256) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_orders PRIMARY KEY CLUSTERED (pk_orders), 
	CONSTRAINT orders_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE orders_shiporder (
	fk_orders INTEGER NOT NULL, 
	fk_shiporder INTEGER NOT NULL, 
	FOREIGN KEY(fk_orders) REFERENCES orders (pk_orders), 
	FOREIGN KEY(fk_shiporder) REFERENCES shiporder (pk_shiporder)
)

CREATE INDEX ix_features_intfeature_with_peculiarly_long_suffix_which_overflow_max_length_fk_intfeature_with_peculiarly_long_suffix_w_ef47 ON features_intfeature_with_peculiarly_long_suffix_which_overflow_max_length (fk_intfeature_with_peculiarly_long_suffix_which_overflow_max_length)

CREATE CLUSTERED INDEX ix_fk_features_intfeature_with_peculiarly_long_suffix_which_overflow_max_length ON features_intfeature_with_peculiarly_long_suffix_which_overflow_max_length (fk_features, fk_intfeature_with_peculiarly_long_suffix_which_overflow_max_length)

CREATE INDEX ix_features_stringfeature_fk_stringfeature ON features_stringfeature (fk_stringfeature)

CREATE CLUSTERED INDEX ix_fk_features_stringfeature ON features_stringfeature (fk_features, fk_stringfeature)

CREATE CLUSTERED INDEX ix_fk_item_detail ON item_detail (fk_item, fk_detail)

CREATE INDEX ix_item_detail_fk_detail ON item_detail (fk_detail)

CREATE CLUSTERED INDEX ix_fk_shiporder_item ON shiporder_item (fk_shiporder, fk_item)

CREATE INDEX ix_shiporder_item_fk_item ON shiporder_item (fk_item)

CREATE CLUSTERED INDEX ix_fk_shiporder_detail_detail_1 ON shiporder_detail_detail_1 (fk_shiporder, fk_detail_1)

CREATE INDEX ix_shiporder_detail_detail_1_fk_detail_1 ON shiporder_detail_detail_1 (fk_detail_1)

CREATE CLUSTERED INDEX ix_fk_orders_shiporder ON orders_shiporder (fk_orders, fk_shiporder)

CREATE INDEX ix_orders_shiporder_fk_shiporder ON orders_shiporder (fk_shiporder)

