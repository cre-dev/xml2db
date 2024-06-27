
CREATE TABLE [contractTradingHours] (
	[pk_contractTradingHours] INTEGER NOT NULL IDENTITY, 
	[startTime] VARCHAR(18) NULL, 
	[endTime] VARCHAR(18) NULL, 
	date VARCHAR(16) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT [cx_pk_contractTradingHours] PRIMARY KEY CLUSTERED ([pk_contractTradingHours]), 
	CONSTRAINT [contractTradingHours_xml2db_record_hash] UNIQUE (xml2db_record_hash)
)


CREATE TABLE [deliveryProfile] (
	[pk_deliveryProfile] INTEGER NOT NULL IDENTITY, 
	[loadDeliveryStartDate] VARCHAR(16) NULL, 
	[loadDeliveryEndDate] VARCHAR(16) NULL, 
	[daysOfTheWeek] VARCHAR(8000) NULL, 
	[loadDeliveryStartTime] VARCHAR(8000) NULL, 
	[loadDeliveryEndTime] VARCHAR(8000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT [cx_pk_deliveryProfile] PRIMARY KEY CLUSTERED ([pk_deliveryProfile]), 
	CONSTRAINT [deliveryProfile_xml2db_record_hash] UNIQUE (xml2db_record_hash)
)


CREATE TABLE [fixingIndex] (
	[pk_fixingIndex] INTEGER NOT NULL IDENTITY, 
	[indexName] VARCHAR(150) NULL, 
	[indexValue] DOUBLE PRECISION NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT [cx_pk_fixingIndex] PRIMARY KEY CLUSTERED ([pk_fixingIndex]), 
	CONSTRAINT [fixingIndex_xml2db_record_hash] UNIQUE (xml2db_record_hash)
)


CREATE TABLE [optionDetails] (
	[pk_optionDetails] INTEGER NOT NULL IDENTITY, 
	[optionStyle] CHAR(1) NULL, 
	[optionType] CHAR(1) NULL, 
	[optionExerciseDate] VARCHAR(8000) NULL, 
	[optionStrikePrice_value] DOUBLE PRECISION NULL, 
	[optionStrikePrice_currency] CHAR(3) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT [cx_pk_optionDetails] PRIMARY KEY CLUSTERED ([pk_optionDetails]), 
	CONSTRAINT [optionDetails_xml2db_record_hash] UNIQUE (xml2db_record_hash)
)


CREATE TABLE [legContractId] (
	[pk_legContractId] INTEGER NOT NULL IDENTITY, 
	[contractId] VARCHAR(50) NULL, 
	[buySellIndicator] CHAR(1) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT [cx_pk_legContractId] PRIMARY KEY CLUSTERED ([pk_legContractId]), 
	CONSTRAINT [legContractId_xml2db_record_hash] UNIQUE (xml2db_record_hash)
)


CREATE TABLE [priceIntervalQuantityDetails] (
	[pk_priceIntervalQuantityDetails] INTEGER NOT NULL IDENTITY, 
	[intervalStartDate] VARCHAR(16) NULL, 
	[intervalEndDate] VARCHAR(16) NULL, 
	[daysOfTheWeek] VARCHAR(1000) NULL, 
	[intervalStartTime] VARCHAR(8000) NULL, 
	[intervalEndTime] VARCHAR(8000) NULL, 
	quantity DOUBLE PRECISION NULL, 
	unit VARCHAR(8) NULL, 
	[priceTimeIntervalQuantity_value] DOUBLE PRECISION NULL, 
	[priceTimeIntervalQuantity_currency] CHAR(3) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT [cx_pk_priceIntervalQuantityDetails] PRIMARY KEY CLUSTERED ([pk_priceIntervalQuantityDetails]), 
	CONSTRAINT [priceIntervalQuantityDetails_xml2db_record_hash] UNIQUE (xml2db_record_hash)
)


CREATE TABLE [clickAndTradeDetails] (
	[pk_clickAndTradeDetails] INTEGER NOT NULL IDENTITY, 
	[orderType] CHAR(3) NULL, 
	[orderCondition] VARCHAR(8000) NULL, 
	[orderStatus] VARCHAR(8000) NULL, 
	[minimumExecuteVolume_value] DOUBLE PRECISION NULL, 
	[minimumExecuteVolume_unit] VARCHAR(8) NULL, 
	[triggerDetails_priceLimit_value] DOUBLE PRECISION NULL, 
	[triggerDetails_priceLimit_currency] CHAR(3) NULL, 
	[triggerDetails_triggerContractId] VARCHAR(50) NULL, 
	[undisclosedVolume_value] DOUBLE PRECISION NULL, 
	[undisclosedVolume_unit] VARCHAR(8) NULL, 
	[orderDuration_duration] CHAR(3) NULL, 
	[orderDuration_expirationDateTime] DATETIMEOFFSET NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT [cx_pk_clickAndTradeDetails] PRIMARY KEY CLUSTERED ([pk_clickAndTradeDetails]), 
	CONSTRAINT [clickAndTradeDetails_xml2db_record_hash] UNIQUE (xml2db_record_hash)
)


CREATE TABLE contract (
	pk_contract INTEGER NOT NULL IDENTITY, 
	[contractId] VARCHAR(50) NULL, 
	[contractName] VARCHAR(200) NULL, 
	[contractType] VARCHAR(5) NULL, 
	[energyCommodity] VARCHAR(8000) NULL, 
	[settlementMethod] CHAR(1) NULL, 
	[organisedMarketPlaceIdentifier_type] CHAR(3) NULL, 
	[organisedMarketPlaceIdentifier_value] VARCHAR(20) NULL, 
	[lastTradingDateTime] DATETIMEOFFSET NULL, 
	[fk_optionDetails] INTEGER NULL, 
	[deliveryPointOrZone] VARCHAR(8000) NULL, 
	[deliveryStartDate] VARCHAR(16) NULL, 
	[deliveryEndDate] VARCHAR(16) NULL, 
	duration CHAR(1) NULL, 
	[loadType] CHAR(2) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT cx_pk_contract PRIMARY KEY CLUSTERED (pk_contract), 
	CONSTRAINT contract_xml2db_record_hash UNIQUE (xml2db_record_hash), 
	FOREIGN KEY([fk_optionDetails]) REFERENCES [optionDetails] ([pk_optionDetails])
)


CREATE TABLE [contract_fixingIndex] (
	fk_contract INTEGER NOT NULL, 
	[fk_fixingIndex] INTEGER NOT NULL, 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract), 
	FOREIGN KEY([fk_fixingIndex]) REFERENCES [fixingIndex] ([pk_fixingIndex])
)


CREATE TABLE [contract_contractTradingHours] (
	fk_contract INTEGER NOT NULL, 
	[fk_contractTradingHours] INTEGER NOT NULL, 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract), 
	FOREIGN KEY([fk_contractTradingHours]) REFERENCES [contractTradingHours] ([pk_contractTradingHours])
)


CREATE TABLE [contract_deliveryProfile] (
	fk_contract INTEGER NOT NULL, 
	[fk_deliveryProfile] INTEGER NOT NULL, 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract), 
	FOREIGN KEY([fk_deliveryProfile]) REFERENCES [deliveryProfile] ([pk_deliveryProfile])
)


CREATE TABLE [legContract] (
	[pk_legContract] INTEGER NOT NULL IDENTITY, 
	fk_contract INTEGER NULL, 
	[buySellIndicator] CHAR(1) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT [cx_pk_legContract] PRIMARY KEY CLUSTERED ([pk_legContract]), 
	CONSTRAINT [legContract_xml2db_record_hash] UNIQUE (xml2db_record_hash), 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract)
)


CREATE TABLE [TradeReport] (
	[pk_TradeReport] INTEGER NOT NULL IDENTITY, 
	[RecordSeqNumber] INTEGER NULL, 
	[idOfMarketParticipant_type] CHAR(3) NULL, 
	[idOfMarketParticipant_value] VARCHAR(20) NULL, 
	[traderID_traderIdForOrganisedMarket] VARCHAR(100) NULL, 
	[traderID_traderIdForMarketParticipant] VARCHAR(100) NULL, 
	[otherMarketParticipant_type] CHAR(3) NULL, 
	[otherMarketParticipant_value] VARCHAR(20) NULL, 
	[beneficiaryIdentification_type] CHAR(3) NULL, 
	[beneficiaryIdentification_value] VARCHAR(20) NULL, 
	[tradingCapacity] CHAR(1) NULL, 
	[buySellIndicator] CHAR(1) NULL, 
	aggressor CHAR(1) NULL, 
	[fk_clickAndTradeDetails] INTEGER NULL, 
	[contractInfo_contractId] VARCHAR(50) NULL, 
	[fk_contractInfo_contract] INTEGER NULL, 
	[organisedMarketPlaceIdentifier_type] CHAR(3) NULL, 
	[organisedMarketPlaceIdentifier_value] VARCHAR(20) NULL, 
	[transactionTime] DATETIMEOFFSET NULL, 
	[executionTime] DATETIMEOFFSET NULL, 
	[uniqueTransactionIdentifier_uniqueTransactionIdentifier] VARCHAR(100) NULL, 
	[uniqueTransactionIdentifier_additionalUtiInfo] VARCHAR(100) NULL, 
	[linkedTransactionId] VARCHAR(8000) NULL, 
	[linkedOrderId] VARCHAR(8000) NULL, 
	[voiceBrokered] VARCHAR(1000) NULL, 
	[priceDetails_price] DOUBLE PRECISION NULL, 
	[priceDetails_priceCurrency] CHAR(3) NULL, 
	[notionalAmountDetails_notionalAmount] DOUBLE PRECISION NULL, 
	[notionalAmountDetails_notionalCurrency] CHAR(3) NULL, 
	quantity_value DOUBLE PRECISION NULL, 
	quantity_unit VARCHAR(8) NULL, 
	[totalNotionalContractQuantity_value] DOUBLE PRECISION NULL, 
	[totalNotionalContractQuantity_unit] VARCHAR(6) NULL, 
	[terminationDate] DATETIMEOFFSET NULL, 
	[actionType] CHAR(1) NULL, 
	[Extra] VARCHAR(1000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT [cx_pk_TradeReport] PRIMARY KEY CLUSTERED ([pk_TradeReport]), 
	CONSTRAINT [TradeReport_xml2db_record_hash] UNIQUE (xml2db_record_hash), 
	FOREIGN KEY([fk_clickAndTradeDetails]) REFERENCES [clickAndTradeDetails] ([pk_clickAndTradeDetails]), 
	FOREIGN KEY([fk_contractInfo_contract]) REFERENCES contract (pk_contract)
)


CREATE TABLE [TradeReport_priceIntervalQuantityDetails] (
	[fk_TradeReport] INTEGER NOT NULL, 
	[fk_priceIntervalQuantityDetails] INTEGER NOT NULL, 
	FOREIGN KEY([fk_TradeReport]) REFERENCES [TradeReport] ([pk_TradeReport]), 
	FOREIGN KEY([fk_priceIntervalQuantityDetails]) REFERENCES [priceIntervalQuantityDetails] ([pk_priceIntervalQuantityDetails])
)


CREATE TABLE [OrderReport] (
	[pk_OrderReport] INTEGER NOT NULL IDENTITY, 
	[RecordSeqNumber] INTEGER NULL, 
	[idOfMarketParticipant_type] CHAR(3) NULL, 
	[idOfMarketParticipant_value] VARCHAR(20) NULL, 
	[traderID_traderIdForOrganisedMarket] VARCHAR(100) NULL, 
	[traderID_traderIdForMarketParticipant] VARCHAR(100) NULL, 
	[beneficiaryIdentification_type] CHAR(3) NULL, 
	[beneficiaryIdentification_value] VARCHAR(20) NULL, 
	[tradingCapacity] CHAR(1) NULL, 
	[buySellIndicator] CHAR(1) NULL, 
	[orderId_uniqueOrderIdentifier] VARCHAR(100) NULL, 
	[orderId_previousOrderIdentifier] VARCHAR(100) NULL, 
	[orderType] CHAR(3) NULL, 
	[orderCondition] VARCHAR(8000) NULL, 
	[orderStatus] VARCHAR(8000) NULL, 
	[minimumExecuteVolume_value] DOUBLE PRECISION NULL, 
	[minimumExecuteVolume_unit] VARCHAR(8) NULL, 
	[triggerDetails_priceLimit_value] DOUBLE PRECISION NULL, 
	[triggerDetails_priceLimit_currency] CHAR(3) NULL, 
	[triggerDetails_triggerContractId] VARCHAR(50) NULL, 
	[undisclosedVolume_value] DOUBLE PRECISION NULL, 
	[undisclosedVolume_unit] VARCHAR(8) NULL, 
	[orderDuration_duration] CHAR(3) NULL, 
	[orderDuration_expirationDateTime] DATETIMEOFFSET NULL, 
	[contractInfo_contractId] VARCHAR(50) NULL, 
	[fk_contractInfo_contract] INTEGER NULL, 
	[organisedMarketPlaceIdentifier_type] CHAR(3) NULL, 
	[organisedMarketPlaceIdentifier_value] VARCHAR(20) NULL, 
	[transactionTime] DATETIMEOFFSET NULL, 
	[originalEntryTime] DATETIMEOFFSET NULL, 
	[linkedOrderId] VARCHAR(8000) NULL, 
	[priceDetails_price] DOUBLE PRECISION NULL, 
	[priceDetails_priceCurrency] CHAR(3) NULL, 
	[notionalAmountDetails_notionalAmount] DOUBLE PRECISION NULL, 
	[notionalAmountDetails_notionalCurrency] CHAR(3) NULL, 
	quantity_value DOUBLE PRECISION NULL, 
	quantity_unit VARCHAR(8) NULL, 
	[totalNotionalContractQuantity_value] DOUBLE PRECISION NULL, 
	[totalNotionalContractQuantity_unit] VARCHAR(6) NULL, 
	[actionType] CHAR(1) NULL, 
	[Extra] VARCHAR(1000) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT [cx_pk_OrderReport] PRIMARY KEY CLUSTERED ([pk_OrderReport]), 
	CONSTRAINT [OrderReport_xml2db_record_hash] UNIQUE (xml2db_record_hash), 
	FOREIGN KEY([fk_contractInfo_contract]) REFERENCES contract (pk_contract)
)


CREATE TABLE [OrderReport_priceIntervalQuantityDetails] (
	[fk_OrderReport] INTEGER NOT NULL, 
	[fk_priceIntervalQuantityDetails] INTEGER NOT NULL, 
	FOREIGN KEY([fk_OrderReport]) REFERENCES [OrderReport] ([pk_OrderReport]), 
	FOREIGN KEY([fk_priceIntervalQuantityDetails]) REFERENCES [priceIntervalQuantityDetails] ([pk_priceIntervalQuantityDetails])
)


CREATE TABLE [OrderReport_contractInfo_legContractId] (
	[fk_OrderReport] INTEGER NOT NULL, 
	[fk_legContractId] INTEGER NOT NULL, 
	FOREIGN KEY([fk_OrderReport]) REFERENCES [OrderReport] ([pk_OrderReport]), 
	FOREIGN KEY([fk_legContractId]) REFERENCES [legContractId] ([pk_legContractId])
)


CREATE TABLE [OrderReport_contractInfo_legContract] (
	[fk_OrderReport] INTEGER NOT NULL, 
	[fk_legContract] INTEGER NOT NULL, 
	FOREIGN KEY([fk_OrderReport]) REFERENCES [OrderReport] ([pk_OrderReport]), 
	FOREIGN KEY([fk_legContract]) REFERENCES [legContract] ([pk_legContract])
)


CREATE TABLE [REMITTable1] (
	[pk_REMITTable1] INTEGER NOT NULL IDENTITY, 
	[reportingEntityID_type] CHAR(3) NULL, 
	[reportingEntityID_value] VARCHAR(20) NULL, 
	input_file_path VARCHAR(256) NULL, 
	xml2db_record_hash BINARY(20) NULL, 
	CONSTRAINT [cx_pk_REMITTable1] PRIMARY KEY CLUSTERED ([pk_REMITTable1]), 
	CONSTRAINT [REMITTable1_xml2db_record_hash] UNIQUE (xml2db_record_hash)
)


CREATE TABLE [REMITTable1_contractList_contract] (
	[fk_REMITTable1] INTEGER NOT NULL, 
	fk_contract INTEGER NOT NULL, 
	FOREIGN KEY([fk_REMITTable1]) REFERENCES [REMITTable1] ([pk_REMITTable1]), 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract)
)


CREATE TABLE [REMITTable1_OrderList_OrderReport] (
	[fk_REMITTable1] INTEGER NOT NULL, 
	[fk_OrderReport] INTEGER NOT NULL, 
	FOREIGN KEY([fk_REMITTable1]) REFERENCES [REMITTable1] ([pk_REMITTable1]), 
	FOREIGN KEY([fk_OrderReport]) REFERENCES [OrderReport] ([pk_OrderReport])
)


CREATE TABLE [REMITTable1_TradeList_TradeReport] (
	[fk_REMITTable1] INTEGER NOT NULL, 
	[fk_TradeReport] INTEGER NOT NULL, 
	FOREIGN KEY([fk_REMITTable1]) REFERENCES [REMITTable1] ([pk_REMITTable1]), 
	FOREIGN KEY([fk_TradeReport]) REFERENCES [TradeReport] ([pk_TradeReport])
)

CREATE INDEX [ix_contract_fixingIndex_fk_fixingIndex] ON [contract_fixingIndex] ([fk_fixingIndex])

CREATE CLUSTERED INDEX [ix_fk_contract_fixingIndex] ON [contract_fixingIndex] (fk_contract, [fk_fixingIndex])

CREATE INDEX [ix_contract_contractTradingHours_fk_contractTradingHours] ON [contract_contractTradingHours] ([fk_contractTradingHours])

CREATE CLUSTERED INDEX [ix_fk_contract_contractTradingHours] ON [contract_contractTradingHours] (fk_contract, [fk_contractTradingHours])

CREATE INDEX [ix_contract_deliveryProfile_fk_deliveryProfile] ON [contract_deliveryProfile] ([fk_deliveryProfile])

CREATE CLUSTERED INDEX [ix_fk_contract_deliveryProfile] ON [contract_deliveryProfile] (fk_contract, [fk_deliveryProfile])

CREATE INDEX [ix_TradeReport_priceIntervalQuantityDetails_fk_priceIntervalQuantityDetails] ON [TradeReport_priceIntervalQuantityDetails] ([fk_priceIntervalQuantityDetails])

CREATE CLUSTERED INDEX [ix_fk_TradeReport_priceIntervalQuantityDetails] ON [TradeReport_priceIntervalQuantityDetails] ([fk_TradeReport], [fk_priceIntervalQuantityDetails])

CREATE INDEX [ix_OrderReport_priceIntervalQuantityDetails_fk_priceIntervalQuantityDetails] ON [OrderReport_priceIntervalQuantityDetails] ([fk_priceIntervalQuantityDetails])

CREATE CLUSTERED INDEX [ix_fk_OrderReport_priceIntervalQuantityDetails] ON [OrderReport_priceIntervalQuantityDetails] ([fk_OrderReport], [fk_priceIntervalQuantityDetails])

CREATE INDEX [ix_OrderReport_contractInfo_legContractId_fk_legContractId] ON [OrderReport_contractInfo_legContractId] ([fk_legContractId])

CREATE CLUSTERED INDEX [ix_fk_OrderReport_contractInfo_legContractId] ON [OrderReport_contractInfo_legContractId] ([fk_OrderReport], [fk_legContractId])

CREATE INDEX [ix_OrderReport_contractInfo_legContract_fk_legContract] ON [OrderReport_contractInfo_legContract] ([fk_legContract])

CREATE CLUSTERED INDEX [ix_fk_OrderReport_contractInfo_legContract] ON [OrderReport_contractInfo_legContract] ([fk_OrderReport], [fk_legContract])

CREATE INDEX [ix_REMITTable1_contractList_contract_fk_contract] ON [REMITTable1_contractList_contract] (fk_contract)

CREATE CLUSTERED INDEX [ix_fk_REMITTable1_contractList_contract] ON [REMITTable1_contractList_contract] ([fk_REMITTable1], fk_contract)

CREATE INDEX [ix_REMITTable1_OrderList_OrderReport_fk_OrderReport] ON [REMITTable1_OrderList_OrderReport] ([fk_OrderReport])

CREATE CLUSTERED INDEX [ix_fk_REMITTable1_OrderList_OrderReport] ON [REMITTable1_OrderList_OrderReport] ([fk_REMITTable1], [fk_OrderReport])

CREATE INDEX [ix_REMITTable1_TradeList_TradeReport_fk_TradeReport] ON [REMITTable1_TradeList_TradeReport] ([fk_TradeReport])

CREATE CLUSTERED INDEX [ix_fk_REMITTable1_TradeList_TradeReport] ON [REMITTable1_TradeList_TradeReport] ([fk_REMITTable1], [fk_TradeReport])

