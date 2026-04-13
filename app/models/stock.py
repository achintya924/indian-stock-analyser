from pydantic import BaseModel
from typing import Optional
from datetime import date


class OHLCVRecord(BaseModel):
    date: str
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    volume: Optional[float]


class OHLCVResponse(BaseModel):
    ticker: str
    exchange: str
    records: list[OHLCVRecord]


class StockInfo(BaseModel):
    ticker: str
    company_name: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    market_cap: Optional[float]
    current_price: Optional[float]
    currency: Optional[str]
    exchange: Optional[str]


class HistoryResponse(BaseModel):
    ticker: str
    period: str
    records: list[OHLCVRecord]


class IndexData(BaseModel):
    name: str
    symbol: str
    current_value: Optional[float]
    previous_close: Optional[float]
    change: Optional[float]
    change_pct: Optional[float]


class IndicesResponse(BaseModel):
    nifty50: IndexData
    sensex: IndexData


class HealthResponse(BaseModel):
    status: str
    app_name: str
    debug: bool
