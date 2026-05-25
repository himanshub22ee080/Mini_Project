from pydantic import BaseModel, Field
from typing import Optional

class ExchangeSchema(BaseModel):
    """The required 20 fields for exchange notifications."""
    exchange_id: Optional[str] = Field(None, description="Unique ID for the exchange")
    notification_type: Optional[str] = Field(None, description="E.g., Trade Confirm, Corporate Action")
    sender_name: Optional[str] = Field(None, description="Entity sending the notification")
    isin: Optional[str] = Field(None, description="International Securities Identification Number")
    ticker: Optional[str] = Field(None, description="Stock Ticker")
    trade_date: Optional[str] = Field(None, description="Date of transaction")
    settlement_date: Optional[str] = Field(None, description="Date of settlement")
    quantity: Optional[float] = Field(None, description="Number of units")
    price: Optional[float] = Field(None, description="Price per unit")
    currency: Optional[str] = Field(None, description="Currency code (USD, EUR)")
    notional_amount: Optional[float] = Field(None, description="Total value")
    counterparty: Optional[str] = Field(None, description="Counterparty name")
    account_number: Optional[str] = Field(None, description="Internal account reference")
    fee_amount: Optional[float] = Field(None, description="Transaction fees")
    tax_amount: Optional[float] = Field(None, description="Applicable taxes")
    venue: Optional[str] = Field(None, description="Trading venue or market")
    status: Optional[str] = Field(None, description="Status of the trade")
    comment: Optional[str] = Field(None, description="General remarks")
    security_description: Optional[str] = Field(None, description="Full name of security")
    transaction_id: Optional[str] = Field(None, description="Exchange-side transaction ID")