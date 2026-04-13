from fastapi import APIRouter, Query
from app.models.stock import OHLCVResponse, StockInfo, HistoryResponse, IndicesResponse
from app.services import stock_service

router = APIRouter()


@router.get("/stock/{ticker}", response_model=OHLCVResponse)
def get_ohlcv(ticker: str):
    """Returns OHLCV data for the last 30 days. Supports NSE (.NS) and BSE (.BO) tickers."""
    return stock_service.get_ohlcv(ticker)


@router.get("/stock/{ticker}/info", response_model=StockInfo)
def get_stock_info(ticker: str):
    """Returns company name, sector, market cap, and current price."""
    return stock_service.get_stock_info(ticker)


@router.get("/stock/{ticker}/history", response_model=HistoryResponse)
def get_history(
    ticker: str,
    period: str = Query(default="1mo", description="Period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max"),
):
    """Returns historical OHLCV data for the given period."""
    return stock_service.get_history(ticker, period)


@router.get("/indices", response_model=IndicesResponse)
def get_indices():
    """Returns current Nifty 50 and Sensex values."""
    return stock_service.get_indices()
