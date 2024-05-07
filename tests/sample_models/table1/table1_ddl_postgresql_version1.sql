
CREATE TABLE "contractTradingHours" (
	"pk_contractTradingHours" SERIAL NOT NULL, 
	"startTime" VARCHAR(18), 
	"endTime" VARCHAR(18), 
	date VARCHAR(16), 
	record_hash BYTEA, 
	CONSTRAINT "cx_pk_contractTradingHours" PRIMARY KEY ("pk_contractTradingHours"), 
	CONSTRAINT "contractTradingHours_xml2db_record_hash" UNIQUE (record_hash)
)


CREATE TABLE "deliveryProfile" (
	"pk_deliveryProfile" SERIAL NOT NULL, 
	"loadDeliveryStartDate" VARCHAR(16), 
	"loadDeliveryEndDate" VARCHAR(16), 
	"daysOfTheWeek" VARCHAR(8000), 
	"loadDeliveryStartTime" VARCHAR(8000), 
	"loadDeliveryEndTime" VARCHAR(8000), 
	record_hash BYTEA, 
	CONSTRAINT "cx_pk_deliveryProfile" PRIMARY KEY ("pk_deliveryProfile"), 
	CONSTRAINT "deliveryProfile_xml2db_record_hash" UNIQUE (record_hash)
)


CREATE TABLE "fixingIndex" (
	"pk_fixingIndex" SERIAL NOT NULL, 
	"indexName" VARCHAR(150), 
	"indexValue" FLOAT, 
	record_hash BYTEA, 
	CONSTRAINT "cx_pk_fixingIndex" PRIMARY KEY ("pk_fixingIndex"), 
	CONSTRAINT "fixingIndex_xml2db_record_hash" UNIQUE (record_hash)
)


CREATE TABLE "optionDetails" (
	"pk_optionDetails" SERIAL NOT NULL, 
	"optionStyle" VARCHAR(1), 
	"optionType" VARCHAR(1), 
	"optionExerciseDate" VARCHAR(8000), 
	"optionStrikePrice_value" FLOAT, 
	"optionStrikePrice_currency" VARCHAR(3), 
	record_hash BYTEA, 
	CONSTRAINT "cx_pk_optionDetails" PRIMARY KEY ("pk_optionDetails"), 
	CONSTRAINT "optionDetails_xml2db_record_hash" UNIQUE (record_hash)
)


CREATE TABLE "priceIntervalQuantityDetails" (
	"pk_priceIntervalQuantityDetails" SERIAL NOT NULL, 
	"intervalStartDate" VARCHAR(16), 
	"intervalEndDate" VARCHAR(16), 
	"daysOfTheWeek" VARCHAR(1000), 
	"intervalStartTime" VARCHAR(8000), 
	"intervalEndTime" VARCHAR(8000), 
	quantity FLOAT, 
	unit VARCHAR(8), 
	"priceTimeIntervalQuantity_value" FLOAT, 
	"priceTimeIntervalQuantity_currency" VARCHAR(3), 
	record_hash BYTEA, 
	CONSTRAINT "cx_pk_priceIntervalQuantityDetails" PRIMARY KEY ("pk_priceIntervalQuantityDetails"), 
	CONSTRAINT "priceIntervalQuantityDetails_xml2db_record_hash" UNIQUE (record_hash)
)


CREATE TABLE "clickAndTradeDetails" (
	"pk_clickAndTradeDetails" SERIAL NOT NULL, 
	"orderType" VARCHAR(3), 
	"orderCondition" VARCHAR(8000), 
	"orderStatus" VARCHAR(8000), 
	"minimumExecuteVolume_value" FLOAT, 
	"minimumExecuteVolume_unit" VARCHAR(8), 
	"triggerDetails_priceLimit_value" FLOAT, 
	"triggerDetails_priceLimit_currency" VARCHAR(3), 
	"triggerDetails_triggerContractId" VARCHAR(50), 
	"undisclosedVolume_value" FLOAT, 
	"undisclosedVolume_unit" VARCHAR(8), 
	"orderDuration_duration" VARCHAR(3), 
	"orderDuration_expirationDateTime" TIMESTAMP WITH TIME ZONE, 
	record_hash BYTEA, 
	CONSTRAINT "cx_pk_clickAndTradeDetails" PRIMARY KEY ("pk_clickAndTradeDetails"), 
	CONSTRAINT "clickAndTradeDetails_xml2db_record_hash" UNIQUE (record_hash)
)


CREATE TABLE contract (
	pk_contract SERIAL NOT NULL, 
	"contractId" VARCHAR(50), 
	"contractName" VARCHAR(200), 
	"contractType" VARCHAR(5), 
	"energyCommodity" VARCHAR(8000), 
	"settlementMethod" VARCHAR(1), 
	"organisedMarketPlaceIdentifier_type" VARCHAR(3), 
	"organisedMarketPlaceIdentifier_value" VARCHAR(20), 
	"lastTradingDateTime" TIMESTAMP WITH TIME ZONE, 
	"fk_optionDetails" INTEGER, 
	"deliveryPointOrZone" VARCHAR(8000), 
	"deliveryStartDate" VARCHAR(16), 
	"deliveryEndDate" VARCHAR(16), 
	duration VARCHAR(1), 
	"loadType" VARCHAR(2), 
	record_hash BYTEA, 
	CONSTRAINT cx_pk_contract PRIMARY KEY (pk_contract), 
	CONSTRAINT contract_xml2db_record_hash UNIQUE (record_hash), 
	FOREIGN KEY("fk_optionDetails") REFERENCES "optionDetails" ("pk_optionDetails")
)


CREATE TABLE "contract_fixingIndex" (
	fk_contract INTEGER NOT NULL, 
	"fk_fixingIndex" INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract), 
	FOREIGN KEY("fk_fixingIndex") REFERENCES "fixingIndex" ("pk_fixingIndex")
)


CREATE TABLE "contract_contractTradingHours" (
	fk_contract INTEGER NOT NULL, 
	"fk_contractTradingHours" INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract), 
	FOREIGN KEY("fk_contractTradingHours") REFERENCES "contractTradingHours" ("pk_contractTradingHours")
)


CREATE TABLE "contract_deliveryProfile" (
	fk_contract INTEGER NOT NULL, 
	"fk_deliveryProfile" INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract), 
	FOREIGN KEY("fk_deliveryProfile") REFERENCES "deliveryProfile" ("pk_deliveryProfile")
)


CREATE TABLE "REMITTable1" (
	"pk_REMITTable1" SERIAL NOT NULL, 
	"reportingEntityID_type" VARCHAR(3), 
	"reportingEntityID_value" VARCHAR(20), 
	xml2db_input_file_path VARCHAR(256) NOT NULL, 
	xml2db_processed_at TIMESTAMP WITH TIME ZONE, 
	record_hash BYTEA, 
	CONSTRAINT "cx_pk_REMITTable1" PRIMARY KEY ("pk_REMITTable1"), 
	CONSTRAINT "REMITTable1_xml2db_record_hash" UNIQUE (record_hash)
)


CREATE TABLE "REMITTable1_contract" (
	"fk_REMITTable1" INTEGER NOT NULL, 
	fk_contract INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY("fk_REMITTable1") REFERENCES "REMITTable1" ("pk_REMITTable1"), 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract)
)


CREATE TABLE "OrderReport" (
	"pk_OrderReport" SERIAL NOT NULL, 
	"temp_pk_OrderReport" INTEGER, 
	"fk_parent_REMITTable1" INTEGER, 
	xml2db_row_number INTEGER NOT NULL, 
	"RecordSeqNumber" INTEGER, 
	"idOfMarketParticipant_type" VARCHAR(3), 
	"idOfMarketParticipant_value" VARCHAR(20), 
	"traderID_traderIdForOrganisedMarket" VARCHAR(100), 
	"traderID_traderIdForMarketParticipant" VARCHAR(100), 
	"beneficiaryIdentification_type" VARCHAR(3), 
	"beneficiaryIdentification_value" VARCHAR(20), 
	"tradingCapacity" VARCHAR(1), 
	"buySellIndicator" VARCHAR(1), 
	"orderId_uniqueOrderIdentifier" VARCHAR(100), 
	"orderId_previousOrderIdentifier" VARCHAR(100), 
	"orderType" VARCHAR(3), 
	"orderCondition" VARCHAR(8000), 
	"orderStatus" VARCHAR(8000), 
	"minimumExecuteVolume_value" FLOAT, 
	"minimumExecuteVolume_unit" VARCHAR(8), 
	"triggerDetails_priceLimit_value" FLOAT, 
	"triggerDetails_priceLimit_currency" VARCHAR(3), 
	"triggerDetails_triggerContractId" VARCHAR(50), 
	"undisclosedVolume_value" FLOAT, 
	"undisclosedVolume_unit" VARCHAR(8), 
	"orderDuration_duration" VARCHAR(3), 
	"orderDuration_expirationDateTime" TIMESTAMP WITH TIME ZONE, 
	"contractInfo_contractId" VARCHAR(50), 
	"fk_contractInfo_contract" INTEGER, 
	"organisedMarketPlaceIdentifier_type" VARCHAR(3), 
	"organisedMarketPlaceIdentifier_value" VARCHAR(20), 
	"transactionTime" TIMESTAMP WITH TIME ZONE, 
	"originalEntryTime" TIMESTAMP WITH TIME ZONE, 
	"linkedOrderId" VARCHAR(8000), 
	"priceDetails_price" FLOAT, 
	"priceDetails_priceCurrency" VARCHAR(3), 
	"notionalAmountDetails_notionalAmount" FLOAT, 
	"notionalAmountDetails_notionalCurrency" VARCHAR(3), 
	quantity_value FLOAT, 
	quantity_unit VARCHAR(8), 
	"totalNotionalContractQuantity_value" FLOAT, 
	"totalNotionalContractQuantity_unit" VARCHAR(6), 
	"actionType" VARCHAR(1), 
	"Extra" VARCHAR(1000), 
	CONSTRAINT "cx_pk_OrderReport" PRIMARY KEY ("pk_OrderReport"), 
	FOREIGN KEY("fk_parent_REMITTable1") REFERENCES "REMITTable1" ("pk_REMITTable1"), 
	FOREIGN KEY("fk_contractInfo_contract") REFERENCES contract (pk_contract)
)


CREATE TABLE "OrderReport_priceIntervalQuantityDetails" (
	"fk_OrderReport" INTEGER NOT NULL, 
	"fk_priceIntervalQuantityDetails" INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY("fk_OrderReport") REFERENCES "OrderReport" ("pk_OrderReport"), 
	FOREIGN KEY("fk_priceIntervalQuantityDetails") REFERENCES "priceIntervalQuantityDetails" ("pk_priceIntervalQuantityDetails")
)


CREATE TABLE "TradeReport" (
	"pk_TradeReport" SERIAL NOT NULL, 
	"temp_pk_TradeReport" INTEGER, 
	"fk_parent_REMITTable1" INTEGER, 
	xml2db_row_number INTEGER NOT NULL, 
	"RecordSeqNumber" INTEGER, 
	"idOfMarketParticipant_type" VARCHAR(3), 
	"idOfMarketParticipant_value" VARCHAR(20), 
	"traderID_traderIdForOrganisedMarket" VARCHAR(100), 
	"traderID_traderIdForMarketParticipant" VARCHAR(100), 
	"otherMarketParticipant_type" VARCHAR(3), 
	"otherMarketParticipant_value" VARCHAR(20), 
	"beneficiaryIdentification_type" VARCHAR(3), 
	"beneficiaryIdentification_value" VARCHAR(20), 
	"tradingCapacity" VARCHAR(1), 
	"buySellIndicator" VARCHAR(1), 
	aggressor VARCHAR(1), 
	"fk_clickAndTradeDetails" INTEGER, 
	"contractInfo_contractId" VARCHAR(50), 
	"fk_contractInfo_contract" INTEGER, 
	"organisedMarketPlaceIdentifier_type" VARCHAR(3), 
	"organisedMarketPlaceIdentifier_value" VARCHAR(20), 
	"transactionTime" TIMESTAMP WITH TIME ZONE, 
	"executionTime" TIMESTAMP WITH TIME ZONE, 
	"uniqueTransactionIdentifier_uniqueTransactionIdentifier" VARCHAR(100), 
	"uniqueTransactionIdentifier_additionalUtiInfo" VARCHAR(100), 
	"linkedTransactionId" VARCHAR(8000), 
	"linkedOrderId" VARCHAR(8000), 
	"voiceBrokered" VARCHAR(1000), 
	"priceDetails_price" FLOAT, 
	"priceDetails_priceCurrency" VARCHAR(3), 
	"notionalAmountDetails_notionalAmount" FLOAT, 
	"notionalAmountDetails_notionalCurrency" VARCHAR(3), 
	quantity_value FLOAT, 
	quantity_unit VARCHAR(8), 
	"totalNotionalContractQuantity_value" FLOAT, 
	"totalNotionalContractQuantity_unit" VARCHAR(6), 
	"terminationDate" TIMESTAMP WITH TIME ZONE, 
	"actionType" VARCHAR(1), 
	"Extra" VARCHAR(1000), 
	CONSTRAINT "cx_pk_TradeReport" PRIMARY KEY ("pk_TradeReport"), 
	FOREIGN KEY("fk_parent_REMITTable1") REFERENCES "REMITTable1" ("pk_REMITTable1"), 
	FOREIGN KEY("fk_clickAndTradeDetails") REFERENCES "clickAndTradeDetails" ("pk_clickAndTradeDetails"), 
	FOREIGN KEY("fk_contractInfo_contract") REFERENCES contract (pk_contract)
)


CREATE TABLE "TradeReport_priceIntervalQuantityDetails" (
	"fk_TradeReport" INTEGER NOT NULL, 
	"fk_priceIntervalQuantityDetails" INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY("fk_TradeReport") REFERENCES "TradeReport" ("pk_TradeReport"), 
	FOREIGN KEY("fk_priceIntervalQuantityDetails") REFERENCES "priceIntervalQuantityDetails" ("pk_priceIntervalQuantityDetails")
)


CREATE TABLE "legContractId" (
	"pk_legContractId" SERIAL NOT NULL, 
	"fk_parent_OrderReport" INTEGER, 
	xml2db_row_number INTEGER NOT NULL, 
	"contractId" VARCHAR(50), 
	"buySellIndicator" VARCHAR(1), 
	CONSTRAINT "cx_pk_legContractId" PRIMARY KEY ("pk_legContractId"), 
	FOREIGN KEY("fk_parent_OrderReport") REFERENCES "OrderReport" ("pk_OrderReport")
)


CREATE TABLE "legContract" (
	"pk_legContract" SERIAL NOT NULL, 
	"fk_parent_OrderReport" INTEGER, 
	xml2db_row_number INTEGER NOT NULL, 
	fk_contract INTEGER, 
	"buySellIndicator" VARCHAR(1), 
	CONSTRAINT "cx_pk_legContract" PRIMARY KEY ("pk_legContract"), 
	FOREIGN KEY("fk_parent_OrderReport") REFERENCES "OrderReport" ("pk_OrderReport"), 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract)
)

CREATE INDEX "idx_contractTradingHours_columnstore" ON "contractTradingHours" ()

CREATE INDEX "idx_deliveryProfile_columnstore" ON "deliveryProfile" ()

CREATE INDEX "idx_fixingIndex_columnstore" ON "fixingIndex" ()

CREATE INDEX "idx_optionDetails_columnstore" ON "optionDetails" ()

CREATE INDEX "idx_priceIntervalQuantityDetails_columnstore" ON "priceIntervalQuantityDetails" ()

CREATE INDEX "idx_clickAndTradeDetails_columnstore" ON "clickAndTradeDetails" ()

CREATE INDEX idx_contract_columnstore ON contract ()

CREATE INDEX "ix_contract_fk_optionDetails" ON contract ("fk_optionDetails")

CREATE INDEX "idx_contract_fixingIndex_columnstore" ON "contract_fixingIndex" ()

CREATE INDEX "ix_contract_fixingIndex_fk_fixingIndex" ON "contract_fixingIndex" ("fk_fixingIndex")

CREATE INDEX "idx_contract_contractTradingHours_columnstore" ON "contract_contractTradingHours" ()

CREATE INDEX "ix_contract_contractTradingHours_fk_contractTradingHours" ON "contract_contractTradingHours" ("fk_contractTradingHours")

CREATE INDEX "idx_contract_deliveryProfile_columnstore" ON "contract_deliveryProfile" ()

CREATE INDEX "ix_contract_deliveryProfile_fk_deliveryProfile" ON "contract_deliveryProfile" ("fk_deliveryProfile")

CREATE INDEX "idx_REMITTable1_columnstore" ON "REMITTable1" ()

CREATE INDEX "idx_REMITTable1_contract_columnstore" ON "REMITTable1_contract" ()

CREATE INDEX "ix_REMITTable1_contract_fk_contract" ON "REMITTable1_contract" (fk_contract)

CREATE INDEX "idx_OrderReport_columnstore" ON "OrderReport" ()

CREATE INDEX "ix_OrderReport_fk_contractInfo_contract" ON "OrderReport" ("fk_contractInfo_contract")

CREATE INDEX "ix_OrderReport_fk_parent_REMITTable1" ON "OrderReport" ("fk_parent_REMITTable1")

CREATE INDEX "idx_OrderReport_priceIntervalQuantityDetails_columnstore" ON "OrderReport_priceIntervalQuantityDetails" ()

CREATE INDEX "ix_OrderReport_priceIntervalQuantityDetails_fk_priceInt_5eb5" ON "OrderReport_priceIntervalQuantityDetails" ("fk_priceIntervalQuantityDetails")

CREATE INDEX "idx_TradeReport_columnstore" ON "TradeReport" ()

CREATE INDEX "ix_TradeReport_fk_clickAndTradeDetails" ON "TradeReport" ("fk_clickAndTradeDetails")

CREATE INDEX "ix_TradeReport_fk_contractInfo_contract" ON "TradeReport" ("fk_contractInfo_contract")

CREATE INDEX "ix_TradeReport_fk_parent_REMITTable1" ON "TradeReport" ("fk_parent_REMITTable1")

CREATE INDEX "idx_TradeReport_priceIntervalQuantityDetails_columnstore" ON "TradeReport_priceIntervalQuantityDetails" ()

CREATE INDEX "ix_TradeReport_priceIntervalQuantityDetails_fk_priceInt_38b7" ON "TradeReport_priceIntervalQuantityDetails" ("fk_priceIntervalQuantityDetails")

CREATE INDEX "idx_legContractId_columnstore" ON "legContractId" ()

CREATE INDEX "ix_legContractId_fk_parent_OrderReport" ON "legContractId" ("fk_parent_OrderReport")

CREATE INDEX "idx_legContract_columnstore" ON "legContract" ()

CREATE INDEX "ix_legContract_fk_contract" ON "legContract" (fk_contract)

CREATE INDEX "ix_legContract_fk_parent_OrderReport" ON "legContract" ("fk_parent_OrderReport")

