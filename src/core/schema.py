from pydantic import BaseModel, Field
from typing import Optional, List

class Underlying(BaseModel):
    instrumentCounter: Optional[int] = None
    isin: Optional[str] = None
    cusip: Optional[str] = None
    sedol: Optional[str] = None
    nameLong: Optional[str] = None
    exchangeTicker: Optional[str] = None
    ticker: Optional[str] = None
    tradingSymbol: Optional[str] = None
    roundLotSize: Optional[float] = None
    tradeCurrencyCode: Optional[str] = None

class NewUnderlying(BaseModel):
    newInstrumentCounter: Optional[int] = None
    newIsin: Optional[str] = None
    newCusip: Optional[str] = None
    newSedol: Optional[str] = None
    newNameLong: Optional[str] = None
    newExchangeTicker: Optional[str] = None
    newTicker: Optional[str] = None
    newTradingSymbol: Optional[str] = None
    newRoundLotSize: Optional[float] = None
    newTradeCurrencyCode: Optional[str] = None
    newCouponRate: Optional[float] = None
    newCurrentAmountOutstanding: Optional[float] = None
    newCurrentNominalCurrencyCode: Optional[str] = None
    newMaturityDate: Optional[str] = None
    newQuantity: Optional[float] = None
    newQuantityCurrencyCode: Optional[str] = None
    newAllocationPercentage: Optional[float] = None

class Dividend(BaseModel):
    dividendType: Optional[str] = None
    dividendGrossAmount: Optional[float] = None
    dividendCurrencyCode: Optional[str] = None

class PreviousReferenceId(BaseModel):
    exchangeReferenceIdCounter: Optional[int] = None
    exchangePreviousReferenceId: Optional[str] = None

class WorkItemReference(BaseModel):
    workItemType: Optional[str] = None
    stormKey: Optional[str] = None
    workItemStatus: Optional[str] = None

class EnDataExtractionSchema(BaseModel):
    """Full mapping for EnData Exchange Notifications"""
    
    # System Identifiers (Added)
    exchangeNotificationId: Optional[str] = Field(None, description="Internal unique business ID (RDU level)")
    enRawDataId: Optional[str] = Field(None, description="Raw data reference (FEED level)")
    
    # Identifiers
    eventSourceUniqueId: Optional[str] = Field(None, description="Unique vendor feed ID")
    
    # Event Information
    eventType: Optional[str] = Field(None, description="E.g., SHARE CONSOLIDATION, STOCK SPLIT")
    eventSubject: Optional[str] = None
    eventSummaryText: Optional[str] = None
    eventStatus: Optional[str] = None
    eventInitialUrl: Optional[str] = None
    events: Optional[List[str]] = Field(None, description="List of attached file names")
    instrumentTypeCode: Optional[str] = None
    strikePriceChangeFlag: Optional[str] = Field(None, description="YES or NO")
    versionChangeFlag: Optional[str] = Field(None, description="YES or NO")
    
    # Exchange & Source
    exchangeCode: Optional[str] = None
    newExchangeCode: Optional[str] = None
    exchangeSourceName: Optional[str] = None
    exchangeReferenceId: Optional[str] = None
    exchangeReferenceCounter: Optional[int] = None
    exchangeTickers: Optional[List[str]] = None
    dataSource: Optional[str] = None
    
    # Product Information
    productName: Optional[str] = None
    newProductName: Optional[str] = None
    productIsin: Optional[str] = None
    newProductIsin: Optional[str] = None
    exchangePrefix: Optional[str] = None
    newExchangePrefix: Optional[str] = None
    series: Optional[List[str]] = None
    
    # Contract Specifications
    contractSize: Optional[float] = None
    newContractSize: Optional[float] = None
    contractMultiplier: Optional[float] = None
    newContractMultiplier: Optional[float] = None
    tickSize: Optional[float] = None
    newTickSize: Optional[float] = None
    blockTradeMinSize: Optional[float] = None
    newBlockTradeMinSize: Optional[float] = None
    adjustmentFactor: Optional[float] = None
    adjustmentFactorOperatorType: Optional[str] = Field(None, description="E.g., MULTIPLY, DIVIDE")
    
    # Position Limits
    spotMonthPositionLimit: Optional[float] = None
    newSpotMonthPositionLimit: Optional[float] = None
    monthPositionLimit: Optional[float] = None
    newMonthPositionLimit: Optional[float] = None
    allMonthsPositionLimit: Optional[float] = None
    newAllMonthsPositionLimit: Optional[float] = None
    
    # Corporate Action
    quantityBefore: Optional[float] = None
    quantityAfter: Optional[float] = None
    distributionRatio: Optional[float] = None
    subscriptionPrice: Optional[float] = None
    subscriptionPriceCurrencyCode: Optional[str] = None
    
    # Key Dates (Expected as ISO Dates or string formats)
    eventPublishDate: Optional[str] = None
    eventInsertDate: Optional[str] = None
    eventEffectiveDate: Optional[str] = None
    lastTradeDate: Optional[str] = None
    newLastTradeDate: Optional[str] = None
    expirationDate: Optional[str] = None
    newExpirationDate: Optional[str] = None
    lastCumDate: Optional[str] = None
    exDate: Optional[str] = None
    recordDate: Optional[str] = None
    payDate: Optional[str] = None
    
    # Nested Arrays
    underlyings: Optional[List[Underlying]] = None
    newUnderlyings: Optional[List[NewUnderlying]] = None
    dividends: Optional[List[Dividend]] = None
    eventPreviousReferenceIds: Optional[List[PreviousReferenceId]] = None
    enWorkItemReference: Optional[List[WorkItemReference]] = None