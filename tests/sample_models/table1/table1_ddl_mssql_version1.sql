
CREATE TABLE [contractTradingHours] (
	[pk_contractTradingHours] INTEGER NOT NULL IDENTITY, 
	[startTime] VARCHAR(18) NULL, 
	[endTime] VARCHAR(18) NULL, 
	date VARCHAR(16) NULL, 
	record_hash IMAGE NULL, 
	CONSTRAINT [cx_pk_contractTradingHours] PRIMARY KEY NONCLUSTERED ([pk_contractTradingHours]), 
	CONSTRAINT [contractTradingHours_xml2db_record_hash] UNIQUE (record_hash)
)


CREATE TABLE [deliveryProfile] (
	[pk_deliveryProfile] INTEGER NOT NULL IDENTITY, 
	[loadDeliveryStartDate] VARCHAR(16) NULL, 
	[loadDeliveryEndDate] VARCHAR(16) NULL, 
	[daysOfTheWeek] VARCHAR(8000) NULL, 
	[loadDeliveryStartTime] VARCHAR(8000) NULL, 
	[loadDeliveryEndTime] VARCHAR(8000) NULL, 
	record_hash IMAGE NULL, 
	CONSTRAINT [cx_pk_deliveryProfile] PRIMARY KEY NONCLUSTERED ([pk_deliveryProfile]), 
	CONSTRAINT [deliveryProfile_xml2db_record_hash] UNIQUE (record_hash)
)


CREATE TABLE [fixingIndex] (
	[pk_fixingIndex] INTEGER NOT NULL IDENTITY, 
	[indexName] VARCHAR(150) NULL, 
	[indexValue] FLOAT NULL, 
	record_hash IMAGE NULL, 
	CONSTRAINT [cx_pk_fixingIndex] PRIMARY KEY NONCLUSTERED ([pk_fixingIndex]), 
	CONSTRAINT [fixingIndex_xml2db_record_hash] UNIQUE (record_hash)
)


CREATE TABLE [optionDetails] (
	[pk_optionDetails] INTEGER NOT NULL IDENTITY, 
	[optionStyle] VARCHAR(1) NULL, 
	[optionType] VARCHAR(1) NULL, 
	[optionExerciseDate] VARCHAR(8000) NULL, 
	[optionStrikePrice_value] FLOAT NULL, 
	[optionStrikePrice_currency] VARCHAR(3) NULL, 
	record_hash IMAGE NULL, 
	CONSTRAINT [cx_pk_optionDetails] PRIMARY KEY NONCLUSTERED ([pk_optionDetails]), 
	CONSTRAINT [optionDetails_xml2db_record_hash] UNIQUE (record_hash)
)


CREATE TABLE [priceIntervalQuantityDetails] (
	[pk_priceIntervalQuantityDetails] INTEGER NOT NULL IDENTITY, 
	[intervalStartDate] VARCHAR(16) NULL, 
	[intervalEndDate] VARCHAR(16) NULL, 
	[daysOfTheWeek] VARCHAR(1000) NULL, 
	[intervalStartTime] VARCHAR(8000) NULL, 
	[intervalEndTime] VARCHAR(8000) NULL, 
	quantity FLOAT NULL, 
	unit VARCHAR(8) NULL, 
	[priceTimeIntervalQuantity_value] FLOAT NULL, 
	[priceTimeIntervalQuantity_currency] VARCHAR(3) NULL, 
	record_hash IMAGE NULL, 
	CONSTRAINT [cx_pk_priceIntervalQuantityDetails] PRIMARY KEY NONCLUSTERED ([pk_priceIntervalQuantityDetails]), 
	CONSTRAINT [priceIntervalQuantityDetails_xml2db_record_hash] UNIQUE (record_hash)
)


CREATE TABLE [clickAndTradeDetails] (
	[pk_clickAndTradeDetails] INTEGER NOT NULL IDENTITY, 
	[orderType] VARCHAR(3) NULL, 
	[orderCondition] VARCHAR(8000) NULL, 
	[orderStatus] VARCHAR(8000) NULL, 
	[minimumExecuteVolume_value] FLOAT NULL, 
	[minimumExecuteVolume_unit] VARCHAR(8) NULL, 
	[triggerDetails_priceLimit_value] FLOAT NULL, 
	[triggerDetails_priceLimit_currency] VARCHAR(3) NULL, 
	[triggerDetails_triggerContractId] VARCHAR(50) NULL, 
	[undisclosedVolume_value] FLOAT NULL, 
	[undisclosedVolume_unit] VARCHAR(8) NULL, 
	[orderDuration_duration] VARCHAR(3) NULL, 
	[orderDuration_expirationDateTime] DATETIMEOFFSET NULL, 
	record_hash IMAGE NULL, 
	CONSTRAINT [cx_pk_clickAndTradeDetails] PRIMARY KEY NONCLUSTERED ([pk_clickAndTradeDetails]), 
	CONSTRAINT [clickAndTradeDetails_xml2db_record_hash] UNIQUE (record_hash)
)


CREATE TABLE contract (
	pk_contract INTEGER NOT NULL IDENTITY, 
	[contractId] VARCHAR(50) NULL, 
	[contractName] VARCHAR(200) NULL, 
	[contractType] VARCHAR(5) NULL, 
	[energyCommodity] VARCHAR(8000) NULL, 
	[settlementMethod] VARCHAR(1) NULL, 
	[organisedMarketPlaceIdentifier_type] VARCHAR(3) NULL, 
	[organisedMarketPlaceIdentifier_value] VARCHAR(20) NULL, 
	[lastTradingDateTime] DATETIMEOFFSET NULL, 
	[fk_optionDetails] INTEGER NULL, 
	[deliveryPointOrZone] VARCHAR(8000) NULL, 
	[deliveryStartDate] VARCHAR(16) NULL, 
	[deliveryEndDate] VARCHAR(16) NULL, 
	duration VARCHAR(1) NULL, 
	[loadType] VARCHAR(2) NULL, 
	record_hash IMAGE NULL, 
	CONSTRAINT cx_pk_contract PRIMARY KEY NONCLUSTERED (pk_contract), 
	CONSTRAINT contract_xml2db_record_hash UNIQUE (record_hash), 
	FOREIGN KEY([fk_optionDetails]) REFERENCES [optionDetails] ([pk_optionDetails])
)


CREATE TABLE [contract_fixingIndex] (
	fk_contract INTEGER NOT NULL, 
	[fk_fixingIndex] INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract), 
	FOREIGN KEY([fk_fixingIndex]) REFERENCES [fixingIndex] ([pk_fixingIndex])
)


CREATE TABLE [contract_contractTradingHours] (
	fk_contract INTEGER NOT NULL, 
	[fk_contractTradingHours] INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract), 
	FOREIGN KEY([fk_contractTradingHours]) REFERENCES [contractTradingHours] ([pk_contractTradingHours])
)


CREATE TABLE [contract_deliveryProfile] (
	fk_contract INTEGER NOT NULL, 
	[fk_deliveryProfile] INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract), 
	FOREIGN KEY([fk_deliveryProfile]) REFERENCES [deliveryProfile] ([pk_deliveryProfile])
)


CREATE TABLE [REMITTable1] (
	[pk_REMITTable1] INTEGER NOT NULL IDENTITY, 
	[reportingEntityID_type] VARCHAR(3) NULL, 
	[reportingEntityID_value] VARCHAR(20) NULL, 
	xml2db_input_file_path VARCHAR(256) NOT NULL, 
	xml2db_processed_at DATETIMEOFFSET NULL, 
	record_hash IMAGE NULL, 
	CONSTRAINT [cx_pk_REMITTable1] PRIMARY KEY NONCLUSTERED ([pk_REMITTable1]), 
	CONSTRAINT [REMITTable1_xml2db_record_hash] UNIQUE (record_hash)
)


CREATE TABLE [REMITTable1_contract] (
	[fk_REMITTable1] INTEGER NOT NULL, 
	fk_contract INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY([fk_REMITTable1]) REFERENCES [REMITTable1] ([pk_REMITTable1]), 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract)
)


CREATE TABLE [OrderReport] (
	[pk_OrderReport] INTEGER NOT NULL IDENTITY, 
	[temp_pk_OrderReport] INTEGER NULL, 
	[fk_parent_REMITTable1] INTEGER NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	[RecordSeqNumber] INTEGER NULL, 
	[idOfMarketParticipant_type] VARCHAR(3) NULL, 
	[idOfMarketParticipant_value] VARCHAR(20) NULL, 
	[traderID_traderIdForOrganisedMarket] VARCHAR(100) NULL, 
	[traderID_traderIdForMarketParticipant] VARCHAR(100) NULL, 
	[beneficiaryIdentification_type] VARCHAR(3) NULL, 
	[beneficiaryIdentification_value] VARCHAR(20) NULL, 
	[tradingCapacity] VARCHAR(1) NULL, 
	[buySellIndicator] VARCHAR(1) NULL, 
	[orderId_uniqueOrderIdentifier] VARCHAR(100) NULL, 
	[orderId_previousOrderIdentifier] VARCHAR(100) NULL, 
	[orderType] VARCHAR(3) NULL, 
	[orderCondition] VARCHAR(8000) NULL, 
	[orderStatus] VARCHAR(8000) NULL, 
	[minimumExecuteVolume_value] FLOAT NULL, 
	[minimumExecuteVolume_unit] VARCHAR(8) NULL, 
	[triggerDetails_priceLimit_value] FLOAT NULL, 
	[triggerDetails_priceLimit_currency] VARCHAR(3) NULL, 
	[triggerDetails_triggerContractId] VARCHAR(50) NULL, 
	[undisclosedVolume_value] FLOAT NULL, 
	[undisclosedVolume_unit] VARCHAR(8) NULL, 
	[orderDuration_duration] VARCHAR(3) NULL, 
	[orderDuration_expirationDateTime] DATETIMEOFFSET NULL, 
	[contractInfo_contractId] VARCHAR(50) NULL, 
	[fk_contractInfo_contract] INTEGER NULL, 
	[organisedMarketPlaceIdentifier_type] VARCHAR(3) NULL, 
	[organisedMarketPlaceIdentifier_value] VARCHAR(20) NULL, 
	[transactionTime] DATETIMEOFFSET NULL, 
	[originalEntryTime] DATETIMEOFFSET NULL, 
	[linkedOrderId] VARCHAR(8000) NULL, 
	[priceDetails_price] FLOAT NULL, 
	[priceDetails_priceCurrency] VARCHAR(3) NULL, 
	[notionalAmountDetails_notionalAmount] FLOAT NULL, 
	[notionalAmountDetails_notionalCurrency] VARCHAR(3) NULL, 
	quantity_value FLOAT NULL, 
	quantity_unit VARCHAR(8) NULL, 
	[totalNotionalContractQuantity_value] FLOAT NULL, 
	[totalNotionalContractQuantity_unit] VARCHAR(6) NULL, 
	[actionType] VARCHAR(1) NULL, 
	[Extra] VARCHAR(1000) NULL, 
	CONSTRAINT [cx_pk_OrderReport] PRIMARY KEY NONCLUSTERED ([pk_OrderReport]), 
	FOREIGN KEY([fk_parent_REMITTable1]) REFERENCES [REMITTable1] ([pk_REMITTable1]), 
	FOREIGN KEY([fk_contractInfo_contract]) REFERENCES contract (pk_contract)
)


CREATE TABLE [OrderReport_priceIntervalQuantityDetails] (
	[fk_OrderReport] INTEGER NOT NULL, 
	[fk_priceIntervalQuantityDetails] INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY([fk_OrderReport]) REFERENCES [OrderReport] ([pk_OrderReport]), 
	FOREIGN KEY([fk_priceIntervalQuantityDetails]) REFERENCES [priceIntervalQuantityDetails] ([pk_priceIntervalQuantityDetails])
)


CREATE TABLE [TradeReport] (
	[pk_TradeReport] INTEGER NOT NULL IDENTITY, 
	[temp_pk_TradeReport] INTEGER NULL, 
	[fk_parent_REMITTable1] INTEGER NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	[RecordSeqNumber] INTEGER NULL, 
	[idOfMarketParticipant_type] VARCHAR(3) NULL, 
	[idOfMarketParticipant_value] VARCHAR(20) NULL, 
	[traderID_traderIdForOrganisedMarket] VARCHAR(100) NULL, 
	[traderID_traderIdForMarketParticipant] VARCHAR(100) NULL, 
	[otherMarketParticipant_type] VARCHAR(3) NULL, 
	[otherMarketParticipant_value] VARCHAR(20) NULL, 
	[beneficiaryIdentification_type] VARCHAR(3) NULL, 
	[beneficiaryIdentification_value] VARCHAR(20) NULL, 
	[tradingCapacity] VARCHAR(1) NULL, 
	[buySellIndicator] VARCHAR(1) NULL, 
	aggressor VARCHAR(1) NULL, 
	[fk_clickAndTradeDetails] INTEGER NULL, 
	[contractInfo_contractId] VARCHAR(50) NULL, 
	[fk_contractInfo_contract] INTEGER NULL, 
	[organisedMarketPlaceIdentifier_type] VARCHAR(3) NULL, 
	[organisedMarketPlaceIdentifier_value] VARCHAR(20) NULL, 
	[transactionTime] DATETIMEOFFSET NULL, 
	[executionTime] DATETIMEOFFSET NULL, 
	[uniqueTransactionIdentifier_uniqueTransactionIdentifier] VARCHAR(100) NULL, 
	[uniqueTransactionIdentifier_additionalUtiInfo] VARCHAR(100) NULL, 
	[linkedTransactionId] VARCHAR(8000) NULL, 
	[linkedOrderId] VARCHAR(8000) NULL, 
	[voiceBrokered] VARCHAR(1000) NULL, 
	[priceDetails_price] FLOAT NULL, 
	[priceDetails_priceCurrency] VARCHAR(3) NULL, 
	[notionalAmountDetails_notionalAmount] FLOAT NULL, 
	[notionalAmountDetails_notionalCurrency] VARCHAR(3) NULL, 
	quantity_value FLOAT NULL, 
	quantity_unit VARCHAR(8) NULL, 
	[totalNotionalContractQuantity_value] FLOAT NULL, 
	[totalNotionalContractQuantity_unit] VARCHAR(6) NULL, 
	[terminationDate] DATETIMEOFFSET NULL, 
	[actionType] VARCHAR(1) NULL, 
	[Extra] VARCHAR(1000) NULL, 
	CONSTRAINT [cx_pk_TradeReport] PRIMARY KEY NONCLUSTERED ([pk_TradeReport]), 
	FOREIGN KEY([fk_parent_REMITTable1]) REFERENCES [REMITTable1] ([pk_REMITTable1]), 
	FOREIGN KEY([fk_clickAndTradeDetails]) REFERENCES [clickAndTradeDetails] ([pk_clickAndTradeDetails]), 
	FOREIGN KEY([fk_contractInfo_contract]) REFERENCES contract (pk_contract)
)


CREATE TABLE [TradeReport_priceIntervalQuantityDetails] (
	[fk_TradeReport] INTEGER NOT NULL, 
	[fk_priceIntervalQuantityDetails] INTEGER NOT NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	FOREIGN KEY([fk_TradeReport]) REFERENCES [TradeReport] ([pk_TradeReport]), 
	FOREIGN KEY([fk_priceIntervalQuantityDetails]) REFERENCES [priceIntervalQuantityDetails] ([pk_priceIntervalQuantityDetails])
)


CREATE TABLE [legContractId] (
	[pk_legContractId] INTEGER NOT NULL IDENTITY, 
	[fk_parent_OrderReport] INTEGER NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	[contractId] VARCHAR(50) NULL, 
	[buySellIndicator] VARCHAR(1) NULL, 
	CONSTRAINT [cx_pk_legContractId] PRIMARY KEY NONCLUSTERED ([pk_legContractId]), 
	FOREIGN KEY([fk_parent_OrderReport]) REFERENCES [OrderReport] ([pk_OrderReport])
)


CREATE TABLE [legContract] (
	[pk_legContract] INTEGER NOT NULL IDENTITY, 
	[fk_parent_OrderReport] INTEGER NULL, 
	xml2db_row_number INTEGER NOT NULL, 
	fk_contract INTEGER NULL, 
	[buySellIndicator] VARCHAR(1) NULL, 
	CONSTRAINT [cx_pk_legContract] PRIMARY KEY NONCLUSTERED ([pk_legContract]), 
	FOREIGN KEY([fk_parent_OrderReport]) REFERENCES [OrderReport] ([pk_OrderReport]), 
	FOREIGN KEY(fk_contract) REFERENCES contract (pk_contract)
)

CREATE CLUSTERED COLUMNSTORE INDEX [idx_contractTradingHours_columnstore] ON [contractTradingHours]

CREATE CLUSTERED COLUMNSTORE INDEX [idx_deliveryProfile_columnstore] ON [deliveryProfile]

CREATE CLUSTERED COLUMNSTORE INDEX [idx_fixingIndex_columnstore] ON [fixingIndex]

CREATE CLUSTERED COLUMNSTORE INDEX [idx_optionDetails_columnstore] ON [optionDetails]

CREATE CLUSTERED COLUMNSTORE INDEX [idx_priceIntervalQuantityDetails_columnstore] ON [priceIntervalQuantityDetails]

CREATE CLUSTERED COLUMNSTORE INDEX [idx_clickAndTradeDetails_columnstore] ON [clickAndTradeDetails]

CREATE CLUSTERED COLUMNSTORE INDEX idx_contract_columnstore ON contract

CREATE INDEX [ix_contract_fk_optionDetails] ON contract ([fk_optionDetails])

CREATE CLUSTERED COLUMNSTORE INDEX [idx_contract_fixingIndex_columnstore] ON [contract_fixingIndex]

CREATE INDEX [ix_contract_fixingIndex_fk_fixingIndex] ON [contract_fixingIndex] ([fk_fixingIndex])

CREATE CLUSTERED COLUMNSTORE INDEX [idx_contract_contractTradingHours_columnstore] ON [contract_contractTradingHours]

CREATE INDEX [ix_contract_contractTradingHours_fk_contractTradingHours] ON [contract_contractTradingHours] ([fk_contractTradingHours])

CREATE CLUSTERED COLUMNSTORE INDEX [idx_contract_deliveryProfile_columnstore] ON [contract_deliveryProfile]

CREATE INDEX [ix_contract_deliveryProfile_fk_deliveryProfile] ON [contract_deliveryProfile] ([fk_deliveryProfile])

CREATE CLUSTERED COLUMNSTORE INDEX [idx_REMITTable1_columnstore] ON [REMITTable1]

CREATE CLUSTERED COLUMNSTORE INDEX [idx_REMITTable1_contract_columnstore] ON [REMITTable1_contract]

CREATE INDEX [ix_REMITTable1_contract_fk_contract] ON [REMITTable1_contract] (fk_contract)

CREATE CLUSTERED COLUMNSTORE INDEX [idx_OrderReport_columnstore] ON [OrderReport]

CREATE INDEX [ix_OrderReport_fk_contractInfo_contract] ON [OrderReport] ([fk_contractInfo_contract])

CREATE INDEX [ix_OrderReport_fk_parent_REMITTable1] ON [OrderReport] ([fk_parent_REMITTable1])

CREATE CLUSTERED COLUMNSTORE INDEX [idx_OrderReport_priceIntervalQuantityDetails_columnstore] ON [OrderReport_priceIntervalQuantityDetails]

CREATE INDEX [ix_OrderReport_priceIntervalQuantityDetails_fk_priceIntervalQuantityDetails] ON [OrderReport_priceIntervalQuantityDetails] ([fk_priceIntervalQuantityDetails])

CREATE CLUSTERED COLUMNSTORE INDEX [idx_TradeReport_columnstore] ON [TradeReport]

CREATE INDEX [ix_TradeReport_fk_clickAndTradeDetails] ON [TradeReport] ([fk_clickAndTradeDetails])

CREATE INDEX [ix_TradeReport_fk_contractInfo_contract] ON [TradeReport] ([fk_contractInfo_contract])

CREATE INDEX [ix_TradeReport_fk_parent_REMITTable1] ON [TradeReport] ([fk_parent_REMITTable1])

CREATE CLUSTERED COLUMNSTORE INDEX [idx_TradeReport_priceIntervalQuantityDetails_columnstore] ON [TradeReport_priceIntervalQuantityDetails]

CREATE INDEX [ix_TradeReport_priceIntervalQuantityDetails_fk_priceIntervalQuantityDetails] ON [TradeReport_priceIntervalQuantityDetails] ([fk_priceIntervalQuantityDetails])

CREATE CLUSTERED COLUMNSTORE INDEX [idx_legContractId_columnstore] ON [legContractId]

CREATE INDEX [ix_legContractId_fk_parent_OrderReport] ON [legContractId] ([fk_parent_OrderReport])

CREATE CLUSTERED COLUMNSTORE INDEX [idx_legContract_columnstore] ON [legContract]

CREATE INDEX [ix_legContract_fk_contract] ON [legContract] (fk_contract)

CREATE INDEX [ix_legContract_fk_parent_OrderReport] ON [legContract] ([fk_parent_OrderReport])

