
CREATE TABLE `contractTradingHours` (
	`pk_contractTradingHours` INTEGER NOT NULL AUTO_INCREMENT, 
	`startTime` VARCHAR(18), 
	`endTime` VARCHAR(18), 
	date VARCHAR(16), 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT `cx_pk_contractTradingHours` PRIMARY KEY (`pk_contractTradingHours`), 
	CONSTRAINT `contractTradingHours_xml2db_record_hash` UNIQUE (xml2db_record_hash)
)


CREATE TABLE `deliveryProfile` (
	`pk_deliveryProfile` INTEGER NOT NULL AUTO_INCREMENT, 
	`loadDeliveryStartDate` VARCHAR(16), 
	`loadDeliveryEndDate` VARCHAR(16), 
	`daysOfTheWeek` VARCHAR(4000), 
	`loadDeliveryStartTime` VARCHAR(4000), 
	`loadDeliveryEndTime` VARCHAR(4000), 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT `cx_pk_deliveryProfile` PRIMARY KEY (`pk_deliveryProfile`), 
	CONSTRAINT `deliveryProfile_xml2db_record_hash` UNIQUE (xml2db_record_hash)
)


CREATE TABLE `fixingIndex` (
	`pk_fixingIndex` INTEGER NOT NULL AUTO_INCREMENT, 
	`indexName` VARCHAR(150), 
	`indexValue` DOUBLE, 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT `cx_pk_fixingIndex` PRIMARY KEY (`pk_fixingIndex`), 
	CONSTRAINT `fixingIndex_xml2db_record_hash` UNIQUE (xml2db_record_hash)
)


CREATE TABLE `optionDetails` (
	`pk_optionDetails` INTEGER NOT NULL AUTO_INCREMENT, 
	`optionStyle` VARCHAR(1), 
	`optionType` VARCHAR(1), 
	`optionExerciseDate` VARCHAR(4000), 
	`optionStrikePrice_value` DOUBLE, 
	`optionStrikePrice_currency` VARCHAR(3), 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT `cx_pk_optionDetails` PRIMARY KEY (`pk_optionDetails`), 
	CONSTRAINT `optionDetails_xml2db_record_hash` UNIQUE (xml2db_record_hash)
)


CREATE TABLE `priceIntervalQuantityDetails` (
	`pk_priceIntervalQuantityDetails` INTEGER NOT NULL AUTO_INCREMENT, 
	`intervalStartDate` VARCHAR(16), 
	`intervalEndDate` VARCHAR(16), 
	`daysOfTheWeek` VARCHAR(255), 
	`intervalStartTime` VARCHAR(4000), 
	`intervalEndTime` VARCHAR(4000), 
	quantity DOUBLE, 
	unit VARCHAR(8), 
	`priceTimeIntervalQuantity_value` DOUBLE, 
	`priceTimeIntervalQuantity_currency` VARCHAR(3), 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT `cx_pk_priceIntervalQuantityDetails` PRIMARY KEY (`pk_priceIntervalQuantityDetails`), 
	CONSTRAINT `priceIntervalQuantityDetails_xml2db_record_hash` UNIQUE (xml2db_record_hash)
)


CREATE TABLE `clickAndTradeDetails` (
	`pk_clickAndTradeDetails` INTEGER NOT NULL AUTO_INCREMENT, 
	`orderType` VARCHAR(3), 
	`orderCondition` VARCHAR(4000), 
	`orderStatus` VARCHAR(4000), 
	`minimumExecuteVolume_value` DOUBLE, 
	`minimumExecuteVolume_unit` VARCHAR(8), 
	`triggerDetails_priceLimit_value` DOUBLE, 
	`triggerDetails_priceLimit_currency` VARCHAR(3), 
	`triggerDetails_triggerContractId` VARCHAR(50), 
	`undisclosedVolume_value` DOUBLE, 
	`undisclosedVolume_unit` VARCHAR(8), 
	`orderDuration_duration` VARCHAR(3), 
	`orderDuration_expirationDateTime` DATETIME, 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT `cx_pk_clickAndTradeDetails` PRIMARY KEY (`pk_clickAndTradeDetails`), 
	CONSTRAINT `clickAndTradeDetails_xml2db_record_hash` UNIQUE (xml2db_record_hash)
)


CREATE TABLE contract (
	pk_contract INTEGER NOT NULL AUTO_INCREMENT, 
	`contractId` VARCHAR(50), 
	`contractName` VARCHAR(200), 
	`contractType` VARCHAR(5), 
	`energyCommodity` VARCHAR(4000), 
	`settlementMethod` VARCHAR(1), 
	`organisedMarketPlaceIdentifier_type` VARCHAR(3), 
	`organisedMarketPlaceIdentifier_value` VARCHAR(20), 
	`lastTradingDateTime` DATETIME, 
	`fk_optionDetails` INTEGER, 
	`deliveryPointOrZone` VARCHAR(4000), 
	`deliveryStartDate` VARCHAR(16), 
	`deliveryEndDate` VARCHAR(16), 
	duration VARCHAR(1), 
	`loadType` VARCHAR(2), 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT cx_pk_contract PRIMARY KEY (pk_contract), 
	CONSTRAINT contract_xml2db_record_hash UNIQUE (xml2db_record_hash), 
	FOREIGN KEY(`fk_optionDetails`) REFERENCES `optionDetails` (`pk_optionDetails`)
)


CREATE TABLE `contract_fixingIndex` (
	fk_contract INTEGER NOT NULL, 
	`fk_fixingIndex` INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract), 
	FOREIGN KEY(`fk_fixingIndex`) REFERENCES `fixingIndex` (`pk_fixingIndex`)
)


CREATE TABLE `contract_contractTradingHours` (
	fk_contract INTEGER NOT NULL, 
	`fk_contractTradingHours` INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract), 
	FOREIGN KEY(`fk_contractTradingHours`) REFERENCES `contractTradingHours` (`pk_contractTradingHours`)
)


CREATE TABLE `contract_deliveryProfile` (
	fk_contract INTEGER NOT NULL, 
	`fk_deliveryProfile` INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract), 
	FOREIGN KEY(`fk_deliveryProfile`) REFERENCES `deliveryProfile` (`pk_deliveryProfile`)
)


CREATE TABLE `REMITTable1` (
	`pk_REMITTable1` INTEGER NOT NULL AUTO_INCREMENT, 
	`reportingEntityID_type` VARCHAR(3), 
	`reportingEntityID_value` VARCHAR(20), 
	xml2db_processed_at DATETIME, 
	input_file_path VARCHAR(256), 
	xml2db_record_hash BINARY(20), 
	CONSTRAINT `cx_pk_REMITTable1` PRIMARY KEY (`pk_REMITTable1`), 
	CONSTRAINT `REMITTable1_xml2db_record_hash` UNIQUE (xml2db_record_hash)
)


CREATE TABLE `REMITTable1_contract` (
	`fk_REMITTable1` INTEGER NOT NULL, 
	fk_contract INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(`fk_REMITTable1`) REFERENCES `REMITTable1` (`pk_REMITTable1`), 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract)
)


CREATE TABLE `OrderReport` (
	`pk_OrderReport` INTEGER NOT NULL AUTO_INCREMENT, 
	`temp_pk_OrderReport` INTEGER, 
	`fk_parent_REMITTable1` INTEGER, 
	xml2db_row_number INTEGER NOT NULL, 
	`RecordSeqNumber` INTEGER, 
	`idOfMarketParticipant_type` VARCHAR(3), 
	`idOfMarketParticipant_value` VARCHAR(20), 
	`traderID_traderIdForOrganisedMarket` VARCHAR(100), 
	`traderID_traderIdForMarketParticipant` VARCHAR(100), 
	`beneficiaryIdentification_type` VARCHAR(3), 
	`beneficiaryIdentification_value` VARCHAR(20), 
	`tradingCapacity` VARCHAR(1), 
	`buySellIndicator` VARCHAR(1), 
	`orderId_uniqueOrderIdentifier` VARCHAR(100), 
	`orderId_previousOrderIdentifier` VARCHAR(100), 
	`orderType` VARCHAR(3), 
	`orderCondition` VARCHAR(4000), 
	`orderStatus` VARCHAR(4000), 
	`minimumExecuteVolume_value` DOUBLE, 
	`minimumExecuteVolume_unit` VARCHAR(8), 
	`triggerDetails_priceLimit_value` DOUBLE, 
	`triggerDetails_priceLimit_currency` VARCHAR(3), 
	`triggerDetails_triggerContractId` VARCHAR(50), 
	`undisclosedVolume_value` DOUBLE, 
	`undisclosedVolume_unit` VARCHAR(8), 
	`orderDuration_duration` VARCHAR(3), 
	`orderDuration_expirationDateTime` DATETIME, 
	`contractInfo_contractId` VARCHAR(50), 
	`fk_contractInfo_contract` INTEGER, 
	`organisedMarketPlaceIdentifier_type` VARCHAR(3), 
	`organisedMarketPlaceIdentifier_value` VARCHAR(20), 
	`transactionTime` DATETIME, 
	`originalEntryTime` DATETIME, 
	`linkedOrderId` VARCHAR(4000), 
	`priceDetails_price` DOUBLE, 
	`priceDetails_priceCurrency` VARCHAR(3), 
	`notionalAmountDetails_notionalAmount` DOUBLE, 
	`notionalAmountDetails_notionalCurrency` VARCHAR(3), 
	quantity_value DOUBLE, 
	quantity_unit VARCHAR(8), 
	`totalNotionalContractQuantity_value` DOUBLE, 
	`totalNotionalContractQuantity_unit` VARCHAR(6), 
	`actionType` VARCHAR(1), 
	`Extra` VARCHAR(1000), 
	CONSTRAINT `cx_pk_OrderReport` PRIMARY KEY (`pk_OrderReport`), 
	FOREIGN KEY(`fk_parent_REMITTable1`) REFERENCES `REMITTable1` (`pk_REMITTable1`), 
	FOREIGN KEY(`fk_contractInfo_contract`) REFERENCES contract (pk_contract)
)


CREATE TABLE `OrderReport_priceIntervalQuantityDetails` (
	`fk_OrderReport` INTEGER NOT NULL, 
	`fk_priceIntervalQuantityDetails` INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(`fk_OrderReport`) REFERENCES `OrderReport` (`pk_OrderReport`), 
	FOREIGN KEY(`fk_priceIntervalQuantityDetails`) REFERENCES `priceIntervalQuantityDetails` (`pk_priceIntervalQuantityDetails`)
)


CREATE TABLE `TradeReport` (
	`pk_TradeReport` INTEGER NOT NULL AUTO_INCREMENT, 
	`temp_pk_TradeReport` INTEGER, 
	`fk_parent_REMITTable1` INTEGER, 
	xml2db_row_number INTEGER NOT NULL, 
	`RecordSeqNumber` INTEGER, 
	`idOfMarketParticipant_type` VARCHAR(3), 
	`idOfMarketParticipant_value` VARCHAR(20), 
	`traderID_traderIdForOrganisedMarket` VARCHAR(100), 
	`traderID_traderIdForMarketParticipant` VARCHAR(100), 
	`otherMarketParticipant_type` VARCHAR(3), 
	`otherMarketParticipant_value` VARCHAR(20), 
	`beneficiaryIdentification_type` VARCHAR(3), 
	`beneficiaryIdentification_value` VARCHAR(20), 
	`tradingCapacity` VARCHAR(1), 
	`buySellIndicator` VARCHAR(1), 
	aggressor VARCHAR(1), 
	`fk_clickAndTradeDetails` INTEGER, 
	`contractInfo_contractId` VARCHAR(50), 
	`fk_contractInfo_contract` INTEGER, 
	`organisedMarketPlaceIdentifier_type` VARCHAR(3), 
	`organisedMarketPlaceIdentifier_value` VARCHAR(20), 
	`transactionTime` DATETIME, 
	`executionTime` DATETIME, 
	`uniqueTransactionIdentifier_uniqueTransactionIdentifier` VARCHAR(100), 
	`uniqueTransactionIdentifier_additionalUtiInfo` VARCHAR(100), 
	`linkedTransactionId` VARCHAR(4000), 
	`linkedOrderId` VARCHAR(4000), 
	`voiceBrokered` VARCHAR(255), 
	`priceDetails_price` DOUBLE, 
	`priceDetails_priceCurrency` VARCHAR(3), 
	`notionalAmountDetails_notionalAmount` DOUBLE, 
	`notionalAmountDetails_notionalCurrency` VARCHAR(3), 
	quantity_value DOUBLE, 
	quantity_unit VARCHAR(8), 
	`totalNotionalContractQuantity_value` DOUBLE, 
	`totalNotionalContractQuantity_unit` VARCHAR(6), 
	`terminationDate` DATETIME, 
	`actionType` VARCHAR(1), 
	`Extra` VARCHAR(1000), 
	CONSTRAINT `cx_pk_TradeReport` PRIMARY KEY (`pk_TradeReport`), 
	FOREIGN KEY(`fk_parent_REMITTable1`) REFERENCES `REMITTable1` (`pk_REMITTable1`), 
	FOREIGN KEY(`fk_clickAndTradeDetails`) REFERENCES `clickAndTradeDetails` (`pk_clickAndTradeDetails`), 
	FOREIGN KEY(`fk_contractInfo_contract`) REFERENCES contract (pk_contract)
)


CREATE TABLE `TradeReport_priceIntervalQuantityDetails` (
	`fk_TradeReport` INTEGER NOT NULL, 
	`fk_priceIntervalQuantityDetails` INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(`fk_TradeReport`) REFERENCES `TradeReport` (`pk_TradeReport`), 
	FOREIGN KEY(`fk_priceIntervalQuantityDetails`) REFERENCES `priceIntervalQuantityDetails` (`pk_priceIntervalQuantityDetails`)
)


CREATE TABLE `legContractId` (
	`pk_legContractId` INTEGER NOT NULL AUTO_INCREMENT, 
	`fk_parent_OrderReport` INTEGER, 
	xml2db_row_number INTEGER NOT NULL, 
	`contractId` VARCHAR(50), 
	`buySellIndicator` VARCHAR(1), 
	CONSTRAINT `cx_pk_legContractId` PRIMARY KEY (`pk_legContractId`), 
	FOREIGN KEY(`fk_parent_OrderReport`) REFERENCES `OrderReport` (`pk_OrderReport`)
)


CREATE TABLE `legContract` (
	`pk_legContract` INTEGER NOT NULL AUTO_INCREMENT, 
	`fk_parent_OrderReport` INTEGER, 
	xml2db_row_number INTEGER NOT NULL, 
	fk_contract INTEGER, 
	`buySellIndicator` VARCHAR(1), 
	CONSTRAINT `cx_pk_legContract` PRIMARY KEY (`pk_legContract`), 
	FOREIGN KEY(`fk_parent_OrderReport`) REFERENCES `OrderReport` (`pk_OrderReport`), 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract)
)

CREATE INDEX `ix_contract_fixingIndex_fk_contract` ON `contract_fixingIndex` (fk_contract)

CREATE INDEX `ix_contract_fixingIndex_fk_fixingIndex` ON `contract_fixingIndex` (`fk_fixingIndex`)

CREATE INDEX `ix_contract_contractTradingHours_fk_contract` ON `contract_contractTradingHours` (fk_contract)

CREATE INDEX `ix_contract_contractTradingHours_fk_contractTradingHours` ON `contract_contractTradingHours` (`fk_contractTradingHours`)

CREATE INDEX `ix_contract_deliveryProfile_fk_contract` ON `contract_deliveryProfile` (fk_contract)

CREATE INDEX `ix_contract_deliveryProfile_fk_deliveryProfile` ON `contract_deliveryProfile` (`fk_deliveryProfile`)

CREATE INDEX `ix_REMITTable1_contract_fk_REMITTable1` ON `REMITTable1_contract` (`fk_REMITTable1`)

CREATE INDEX `ix_REMITTable1_contract_fk_contract` ON `REMITTable1_contract` (fk_contract)

CREATE INDEX `OrderReport_fk_parent_REMITTable1_idx` ON `OrderReport` (`fk_parent_REMITTable1`)

CREATE INDEX `ix_OrderReport_priceIntervalQuantityDetails_fk_OrderReport` ON `OrderReport_priceIntervalQuantityDetails` (`fk_OrderReport`)

CREATE INDEX `ix_OrderReport_priceIntervalQuantityDetails_fk_priceInte_5eb5` ON `OrderReport_priceIntervalQuantityDetails` (`fk_priceIntervalQuantityDetails`)

CREATE INDEX `TradeReport_fk_parent_REMITTable1_idx` ON `TradeReport` (`fk_parent_REMITTable1`)

CREATE INDEX `ix_TradeReport_priceIntervalQuantityDetails_fk_TradeReport` ON `TradeReport_priceIntervalQuantityDetails` (`fk_TradeReport`)

CREATE INDEX `ix_TradeReport_priceIntervalQuantityDetails_fk_priceInte_38b7` ON `TradeReport_priceIntervalQuantityDetails` (`fk_priceIntervalQuantityDetails`)

