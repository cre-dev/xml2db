
CREATE TABLE error (
	pk_error SERIAL NOT NULL, 
	type VARCHAR(1000), 
	message VARCHAR(1000), 
	value VARCHAR(1000), 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_error PRIMARY KEY (pk_error), 
	CONSTRAINT error_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE failure (
	pk_failure SERIAL NOT NULL, 
	type VARCHAR(1000), 
	message VARCHAR(1000), 
	value VARCHAR(1000), 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_failure PRIMARY KEY (pk_failure), 
	CONSTRAINT failure_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE property (
	pk_property SERIAL NOT NULL, 
	name VARCHAR(1000), 
	value VARCHAR(1000), 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_property PRIMARY KEY (pk_property), 
	CONSTRAINT property_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE "flakyError" (
	"pk_flakyError" SERIAL NOT NULL, 
	message VARCHAR(1000), 
	type VARCHAR(1000), 
	"stackTrace" VARCHAR(1000), 
	"system-out" VARCHAR(1000), 
	"system-err" VARCHAR(1000), 
	value VARCHAR(1000), 
	xml2db_record_hash BYTEA, 
	CONSTRAINT "cx_pk_flakyError" PRIMARY KEY ("pk_flakyError"), 
	CONSTRAINT "flakyError_xml2db_record_hash" UNIQUE (xml2db_record_hash)
)


CREATE TABLE skipped (
	pk_skipped SERIAL NOT NULL, 
	type VARCHAR(1000), 
	message VARCHAR(1000), 
	value VARCHAR(1000), 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_skipped PRIMARY KEY (pk_skipped), 
	CONSTRAINT skipped_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE properties (
	pk_properties SERIAL NOT NULL, 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_properties PRIMARY KEY (pk_properties), 
	CONSTRAINT properties_xml2db_record_hash UNIQUE (xml2db_record_hash)
)


CREATE TABLE properties_property (
	fk_properties INTEGER NOT NULL, 
	fk_property INTEGER NOT NULL, 
	FOREIGN KEY(fk_properties) REFERENCES properties (pk_properties), 
	FOREIGN KEY(fk_property) REFERENCES property (pk_property)
)


CREATE TABLE testcase (
	pk_testcase SERIAL NOT NULL, 
	classname VARCHAR(1000), 
	name VARCHAR(1000), 
	time VARCHAR(1000), 
	"group" VARCHAR(1000), 
	"system-out" VARCHAR(8000), 
	"system-err" VARCHAR(8000), 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_testcase PRIMARY KEY (pk_testcase), 
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


CREATE TABLE "testcase_rerunFailure_flakyError" (
	fk_testcase INTEGER NOT NULL, 
	"fk_flakyError" INTEGER NOT NULL, 
	FOREIGN KEY(fk_testcase) REFERENCES testcase (pk_testcase), 
	FOREIGN KEY("fk_flakyError") REFERENCES "flakyError" ("pk_flakyError")
)


CREATE TABLE "testcase_rerunError_flakyError" (
	fk_testcase INTEGER NOT NULL, 
	"fk_flakyError" INTEGER NOT NULL, 
	FOREIGN KEY(fk_testcase) REFERENCES testcase (pk_testcase), 
	FOREIGN KEY("fk_flakyError") REFERENCES "flakyError" ("pk_flakyError")
)


CREATE TABLE "testcase_flakyFailure_flakyError" (
	fk_testcase INTEGER NOT NULL, 
	"fk_flakyError" INTEGER NOT NULL, 
	FOREIGN KEY(fk_testcase) REFERENCES testcase (pk_testcase), 
	FOREIGN KEY("fk_flakyError") REFERENCES "flakyError" ("pk_flakyError")
)


CREATE TABLE "testcase_flakyError" (
	fk_testcase INTEGER NOT NULL, 
	"fk_flakyError" INTEGER NOT NULL, 
	FOREIGN KEY(fk_testcase) REFERENCES testcase (pk_testcase), 
	FOREIGN KEY("fk_flakyError") REFERENCES "flakyError" ("pk_flakyError")
)


CREATE TABLE testsuite (
	pk_testsuite SERIAL NOT NULL, 
	name VARCHAR(1000), 
	errors VARCHAR(1000), 
	failures VARCHAR(1000), 
	skipped VARCHAR(1000), 
	tests VARCHAR(1000), 
	"group" VARCHAR(1000), 
	time VARCHAR(1000), 
	timestamp VARCHAR(1000), 
	hostname VARCHAR(1000), 
	id VARCHAR(1000), 
	package VARCHAR(1000), 
	file VARCHAR(1000), 
	log VARCHAR(1000), 
	url VARCHAR(1000), 
	version VARCHAR(1000), 
	"system-out" VARCHAR(8000), 
	"system-err" VARCHAR(8000), 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_testsuite PRIMARY KEY (pk_testsuite), 
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


CREATE TABLE junit10 (
	pk_junit10 SERIAL NOT NULL, 
	fk_error INTEGER, 
	fk_failure INTEGER, 
	"fk_flakyError" INTEGER, 
	"flakyFailure_fk_flakyError" INTEGER, 
	fk_properties INTEGER, 
	fk_property INTEGER, 
	"rerunError_fk_flakyError" INTEGER, 
	"rerunFailure_fk_flakyError" INTEGER, 
	fk_skipped INTEGER, 
	"system-err" VARCHAR(1000), 
	"system-out" VARCHAR(1000), 
	fk_testcase INTEGER, 
	fk_testsuite INTEGER, 
	testsuites_name VARCHAR(1000), 
	testsuites_time VARCHAR(1000), 
	testsuites_tests VARCHAR(1000), 
	testsuites_failures VARCHAR(1000), 
	testsuites_errors VARCHAR(1000), 
	input_file_path VARCHAR(256), 
	xml2db_record_hash BYTEA, 
	CONSTRAINT cx_pk_junit10 PRIMARY KEY (pk_junit10), 
	CONSTRAINT junit10_xml2db_record_hash UNIQUE (xml2db_record_hash), 
	FOREIGN KEY(fk_error) REFERENCES error (pk_error), 
	FOREIGN KEY(fk_failure) REFERENCES failure (pk_failure), 
	FOREIGN KEY("fk_flakyError") REFERENCES "flakyError" ("pk_flakyError"), 
	FOREIGN KEY("flakyFailure_fk_flakyError") REFERENCES "flakyError" ("pk_flakyError"), 
	FOREIGN KEY(fk_properties) REFERENCES properties (pk_properties), 
	FOREIGN KEY(fk_property) REFERENCES property (pk_property), 
	FOREIGN KEY("rerunError_fk_flakyError") REFERENCES "flakyError" ("pk_flakyError"), 
	FOREIGN KEY("rerunFailure_fk_flakyError") REFERENCES "flakyError" ("pk_flakyError"), 
	FOREIGN KEY(fk_skipped) REFERENCES skipped (pk_skipped), 
	FOREIGN KEY(fk_testcase) REFERENCES testcase (pk_testcase), 
	FOREIGN KEY(fk_testsuite) REFERENCES testsuite (pk_testsuite)
)


CREATE TABLE junit10_testsuites_testsuite (
	fk_junit10 INTEGER NOT NULL, 
	fk_testsuite INTEGER NOT NULL, 
	FOREIGN KEY(fk_junit10) REFERENCES junit10 (pk_junit10), 
	FOREIGN KEY(fk_testsuite) REFERENCES testsuite (pk_testsuite)
)

CREATE INDEX ix_properties_property_fk_properties ON properties_property (fk_properties)

CREATE INDEX ix_properties_property_fk_property ON properties_property (fk_property)

CREATE INDEX ix_testcase_skipped_fk_skipped ON testcase_skipped (fk_skipped)

CREATE INDEX ix_testcase_skipped_fk_testcase ON testcase_skipped (fk_testcase)

CREATE INDEX ix_testcase_error_fk_error ON testcase_error (fk_error)

CREATE INDEX ix_testcase_error_fk_testcase ON testcase_error (fk_testcase)

CREATE INDEX ix_testcase_failure_fk_failure ON testcase_failure (fk_failure)

CREATE INDEX ix_testcase_failure_fk_testcase ON testcase_failure (fk_testcase)

CREATE INDEX "ix_testcase_rerunFailure_flakyError_fk_flakyError" ON "testcase_rerunFailure_flakyError" ("fk_flakyError")

CREATE INDEX "ix_testcase_rerunFailure_flakyError_fk_testcase" ON "testcase_rerunFailure_flakyError" (fk_testcase)

CREATE INDEX "ix_testcase_rerunError_flakyError_fk_flakyError" ON "testcase_rerunError_flakyError" ("fk_flakyError")

CREATE INDEX "ix_testcase_rerunError_flakyError_fk_testcase" ON "testcase_rerunError_flakyError" (fk_testcase)

CREATE INDEX "ix_testcase_flakyFailure_flakyError_fk_flakyError" ON "testcase_flakyFailure_flakyError" ("fk_flakyError")

CREATE INDEX "ix_testcase_flakyFailure_flakyError_fk_testcase" ON "testcase_flakyFailure_flakyError" (fk_testcase)

CREATE INDEX "ix_testcase_flakyError_fk_flakyError" ON "testcase_flakyError" ("fk_flakyError")

CREATE INDEX "ix_testcase_flakyError_fk_testcase" ON "testcase_flakyError" (fk_testcase)

CREATE INDEX ix_testsuite_properties_fk_properties ON testsuite_properties (fk_properties)

CREATE INDEX ix_testsuite_properties_fk_testsuite ON testsuite_properties (fk_testsuite)

CREATE INDEX ix_testsuite_testcase_fk_testcase ON testsuite_testcase (fk_testcase)

CREATE INDEX ix_testsuite_testcase_fk_testsuite ON testsuite_testcase (fk_testsuite)

CREATE INDEX ix_junit10_testsuites_testsuite_fk_junit10 ON junit10_testsuites_testsuite (fk_junit10)

CREATE INDEX ix_junit10_testsuites_testsuite_fk_testsuite ON junit10_testsuites_testsuite (fk_testsuite)

