
CREATE TABLE error (
	pk_error INTEGER NOT NULL IDENTITY, 
	type VARCHAR(1000) NULL, 
	message VARCHAR(1000) NULL, 
	value VARCHAR(1000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_error PRIMARY KEY CLUSTERED (pk_error), 
	CONSTRAINT error_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE failure (
	pk_failure INTEGER NOT NULL IDENTITY, 
	type VARCHAR(1000) NULL, 
	message VARCHAR(1000) NULL, 
	value VARCHAR(1000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_failure PRIMARY KEY CLUSTERED (pk_failure), 
	CONSTRAINT failure_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE property (
	pk_property INTEGER NOT NULL IDENTITY, 
	name VARCHAR(1000) NULL, 
	value VARCHAR(1000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_property PRIMARY KEY CLUSTERED (pk_property), 
	CONSTRAINT property_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE [flakyError] (
	[pk_flakyError] INTEGER NOT NULL IDENTITY, 
	message VARCHAR(1000) NULL, 
	type VARCHAR(1000) NULL, 
	[stackTrace] VARCHAR(1000) NULL, 
	[system-out] VARCHAR(1000) NULL, 
	[system-err] VARCHAR(1000) NULL, 
	value VARCHAR(1000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT [cx_pk_flakyError] PRIMARY KEY CLUSTERED ([pk_flakyError]), 
	CONSTRAINT [flakyError_xml2db_record_hash] UNIQUE (xml2db_record_hash)
)


CREATE TABLE skipped (
	pk_skipped INTEGER NOT NULL IDENTITY, 
	type VARCHAR(1000) NULL, 
	message VARCHAR(1000) NULL, 
	value VARCHAR(1000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_skipped PRIMARY KEY CLUSTERED (pk_skipped), 
	CONSTRAINT skipped_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE properties (
	pk_properties INTEGER NOT NULL IDENTITY, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_properties PRIMARY KEY CLUSTERED (pk_properties), 
	CONSTRAINT properties_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE properties_property (
	fk_properties INTEGER NOT NULL, 
	fk_property INTEGER NOT NULL, 
	FOREIGN KEY(fk_properties) REFERENCES properties (pk_properties), 
	FOREIGN KEY(fk_property) REFERENCES property (pk_property)
)


CREATE TABLE testcase (
	pk_testcase INTEGER NOT NULL IDENTITY, 
	classname VARCHAR(1000) NULL, 
	name VARCHAR(1000) NULL, 
	time VARCHAR(1000) NULL, 
	[group] VARCHAR(1000) NULL, 
	[system-out] VARCHAR(8000) NULL, 
	[system-err] VARCHAR(8000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_testcase PRIMARY KEY CLUSTERED (pk_testcase), 
	CONSTRAINT testcase_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE testcase_skipped (
	fk_testcase INTEGER NOT NULL, 
	fk_skipped INTEGER NOT NULL, 
	FOREIGN KEY(fk_testcase) REFERENCES testcase (pk_testcase), 
	FOREIGN KEY(fk_skipped) REFERENCES skipped (pk_skipped)
)


CREATE TABLE testcase_error (
	fk_testcase INTEGER NOT NULL, 
	fk_error INTEGER NOT NULL, 
	FOREIGN KEY(fk_testcase) REFERENCES testcase (pk_testcase), 
	FOREIGN KEY(fk_error) REFERENCES error (pk_error)
)


CREATE TABLE testcase_failure (
	fk_testcase INTEGER NOT NULL, 
	fk_failure INTEGER NOT NULL, 
	FOREIGN KEY(fk_testcase) REFERENCES testcase (pk_testcase), 
	FOREIGN KEY(fk_failure) REFERENCES failure (pk_failure)
)


CREATE TABLE [testcase_rerunFailure_flakyError] (
	fk_testcase INTEGER NOT NULL, 
	[fk_flakyError] INTEGER NOT NULL, 
	FOREIGN KEY(fk_testcase) REFERENCES testcase (pk_testcase), 
	FOREIGN KEY([fk_flakyError]) REFERENCES [flakyError] ([pk_flakyError])
)


CREATE TABLE [testcase_rerunError_flakyError] (
	fk_testcase INTEGER NOT NULL, 
	[fk_flakyError] INTEGER NOT NULL, 
	FOREIGN KEY(fk_testcase) REFERENCES testcase (pk_testcase), 
	FOREIGN KEY([fk_flakyError]) REFERENCES [flakyError] ([pk_flakyError])
)


CREATE TABLE [testcase_flakyFailure_flakyError] (
	fk_testcase INTEGER NOT NULL, 
	[fk_flakyError] INTEGER NOT NULL, 
	FOREIGN KEY(fk_testcase) REFERENCES testcase (pk_testcase), 
	FOREIGN KEY([fk_flakyError]) REFERENCES [flakyError] ([pk_flakyError])
)


CREATE TABLE [testcase_flakyError] (
	fk_testcase INTEGER NOT NULL, 
	[fk_flakyError] INTEGER NOT NULL, 
	FOREIGN KEY(fk_testcase) REFERENCES testcase (pk_testcase), 
	FOREIGN KEY([fk_flakyError]) REFERENCES [flakyError] ([pk_flakyError])
)


CREATE TABLE testsuite (
	pk_testsuite INTEGER NOT NULL IDENTITY, 
	name VARCHAR(1000) NULL, 
	errors VARCHAR(1000) NULL, 
	failures VARCHAR(1000) NULL, 
	skipped VARCHAR(1000) NULL, 
	tests VARCHAR(1000) NULL, 
	[group] VARCHAR(1000) NULL, 
	time VARCHAR(1000) NULL, 
	timestamp VARCHAR(1000) NULL, 
	hostname VARCHAR(1000) NULL, 
	id VARCHAR(1000) NULL, 
	package VARCHAR(1000) NULL, 
	[file] VARCHAR(1000) NULL, 
	log VARCHAR(1000) NULL, 
	url VARCHAR(1000) NULL, 
	version VARCHAR(1000) NULL, 
	[system-out] VARCHAR(8000) NULL, 
	[system-err] VARCHAR(8000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_testsuite PRIMARY KEY CLUSTERED (pk_testsuite), 
	CONSTRAINT testsuite_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE testsuite_properties (
	fk_testsuite INTEGER NOT NULL, 
	fk_properties INTEGER NOT NULL, 
	FOREIGN KEY(fk_testsuite) REFERENCES testsuite (pk_testsuite), 
	FOREIGN KEY(fk_properties) REFERENCES properties (pk_properties)
)


CREATE TABLE testsuite_testcase (
	fk_testsuite INTEGER NOT NULL, 
	fk_testcase INTEGER NOT NULL, 
	FOREIGN KEY(fk_testsuite) REFERENCES testsuite (pk_testsuite), 
	FOREIGN KEY(fk_testcase) REFERENCES testcase (pk_testcase)
)


CREATE TABLE testsuites (
	pk_testsuites INTEGER NOT NULL IDENTITY, 
	name VARCHAR(1000) NULL, 
	time VARCHAR(1000) NULL, 
	tests VARCHAR(1000) NULL, 
	failures VARCHAR(1000) NULL, 
	errors VARCHAR(1000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_testsuites PRIMARY KEY CLUSTERED (pk_testsuites), 
	CONSTRAINT testsuites_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE testsuites_testsuite (
	fk_testsuites INTEGER NOT NULL, 
	fk_testsuite INTEGER NOT NULL, 
	FOREIGN KEY(fk_testsuites) REFERENCES testsuites (pk_testsuites), 
	FOREIGN KEY(fk_testsuite) REFERENCES testsuite (pk_testsuite)
)


CREATE TABLE junit10 (
	pk_junit10 INTEGER NOT NULL IDENTITY, 
	fk_error INTEGER NULL, 
	fk_failure INTEGER NULL, 
	[fk_flakyError] INTEGER NULL, 
	[flakyFailure_fk_flakyError] INTEGER NULL, 
	fk_properties INTEGER NULL, 
	fk_property INTEGER NULL, 
	[rerunError_fk_flakyError] INTEGER NULL, 
	[rerunFailure_fk_flakyError] INTEGER NULL, 
	fk_skipped INTEGER NULL, 
	[system-err] VARCHAR(1000) NULL, 
	[system-out] VARCHAR(1000) NULL, 
	fk_testcase INTEGER NULL, 
	fk_testsuite INTEGER NULL, 
	fk_testsuites INTEGER NULL, 
	input_file_path VARCHAR(256) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_junit10 PRIMARY KEY CLUSTERED (pk_junit10), 
	CONSTRAINT junit10_xml2db_record_hash UNIQUE (xml2db_record_hash), 
	FOREIGN KEY(fk_error) REFERENCES error (pk_error), 
	FOREIGN KEY(fk_failure) REFERENCES failure (pk_failure), 
	FOREIGN KEY([fk_flakyError]) REFERENCES [flakyError] ([pk_flakyError]), 
	FOREIGN KEY([flakyFailure_fk_flakyError]) REFERENCES [flakyError] ([pk_flakyError]), 
	FOREIGN KEY(fk_properties) REFERENCES properties (pk_properties), 
	FOREIGN KEY(fk_property) REFERENCES property (pk_property), 
	FOREIGN KEY([rerunError_fk_flakyError]) REFERENCES [flakyError] ([pk_flakyError]), 
	FOREIGN KEY([rerunFailure_fk_flakyError]) REFERENCES [flakyError] ([pk_flakyError]), 
	FOREIGN KEY(fk_skipped) REFERENCES skipped (pk_skipped), 
	FOREIGN KEY(fk_testcase) REFERENCES testcase (pk_testcase), 
	FOREIGN KEY(fk_testsuite) REFERENCES testsuite (pk_testsuite), 
	FOREIGN KEY(fk_testsuites) REFERENCES testsuites (pk_testsuites)
)

CREATE CLUSTERED INDEX ix_fk_properties_property ON properties_property (fk_properties, fk_property)

CREATE INDEX ix_properties_property_fk_property ON properties_property (fk_property)

CREATE CLUSTERED INDEX ix_fk_testcase_skipped ON testcase_skipped (fk_testcase, fk_skipped)

CREATE INDEX ix_testcase_skipped_fk_skipped ON testcase_skipped (fk_skipped)

CREATE CLUSTERED INDEX ix_fk_testcase_error ON testcase_error (fk_testcase, fk_error)

CREATE INDEX ix_testcase_error_fk_error ON testcase_error (fk_error)

CREATE CLUSTERED INDEX ix_fk_testcase_failure ON testcase_failure (fk_testcase, fk_failure)

CREATE INDEX ix_testcase_failure_fk_failure ON testcase_failure (fk_failure)

CREATE CLUSTERED INDEX [ix_fk_testcase_rerunFailure_flakyError] ON [testcase_rerunFailure_flakyError] (fk_testcase, [fk_flakyError])

CREATE INDEX [ix_testcase_rerunFailure_flakyError_fk_flakyError] ON [testcase_rerunFailure_flakyError] ([fk_flakyError])

CREATE CLUSTERED INDEX [ix_fk_testcase_rerunError_flakyError] ON [testcase_rerunError_flakyError] (fk_testcase, [fk_flakyError])

CREATE INDEX [ix_testcase_rerunError_flakyError_fk_flakyError] ON [testcase_rerunError_flakyError] ([fk_flakyError])

CREATE CLUSTERED INDEX [ix_fk_testcase_flakyFailure_flakyError] ON [testcase_flakyFailure_flakyError] (fk_testcase, [fk_flakyError])

CREATE INDEX [ix_testcase_flakyFailure_flakyError_fk_flakyError] ON [testcase_flakyFailure_flakyError] ([fk_flakyError])

CREATE CLUSTERED INDEX [ix_fk_testcase_flakyError] ON [testcase_flakyError] (fk_testcase, [fk_flakyError])

CREATE INDEX [ix_testcase_flakyError_fk_flakyError] ON [testcase_flakyError] ([fk_flakyError])

CREATE CLUSTERED INDEX ix_fk_testsuite_properties ON testsuite_properties (fk_testsuite, fk_properties)

CREATE INDEX ix_testsuite_properties_fk_properties ON testsuite_properties (fk_properties)

CREATE CLUSTERED INDEX ix_fk_testsuite_testcase ON testsuite_testcase (fk_testsuite, fk_testcase)

CREATE INDEX ix_testsuite_testcase_fk_testcase ON testsuite_testcase (fk_testcase)

CREATE CLUSTERED INDEX ix_fk_testsuites_testsuite ON testsuites_testsuite (fk_testsuites, fk_testsuite)

CREATE INDEX ix_testsuites_testsuite_fk_testsuite ON testsuites_testsuite (fk_testsuite)

