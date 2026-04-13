import yfinance as yf
import pandas as pd
from fastapi import HTTPException
from yfinance.exceptions import YFRateLimitError, YFPricesMissingError, YFInvalidPeriodError
from app.models.stock import (
    OHLCVRecord,
    OHLCVResponse,
    StockInfo,
    HistoryResponse,
    IndexData,
    IndicesResponse,
)

VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}


def normalize_ticker(ticker: str) -> str:
    """Auto-append .NS if no exchange suffix is provided."""
    ticker = ticker.upper()
    if not ticker.endswith(".NS") and not ticker.endswith(".BO"):
        ticker = ticker + ".NS"
    return ticker


def _detect_exchange(ticker: str) -> str:
    if ticker.endswith(".NS"):
        return "NSE"
    if ticker.endswith(".BO"):
        return "BSE"
    return "UNKNOWN"


def _df_to_ohlcv_records(df: pd.DataFrame) -> list[OHLCVRecord]:
    records = []
    for idx, row in df.iterrows():
        date_str = str(idx.date()) if hasattr(idx, "date") else str(idx)
        records.append(
            OHLCVRecord(
                date=date_str,
                open=round(float(row["Open"]), 2) if pd.notna(row["Open"]) else None,
                high=round(float(row["High"]), 2) if pd.notna(row["High"]) else None,
                low=round(float(row["Low"]), 2) if pd.notna(row["Low"]) else None,
                close=round(float(row["Close"]), 2) if pd.notna(row["Close"]) else None,
                volume=float(row["Volume"]) if pd.notna(row["Volume"]) else None,
            )
        )
    return records


def get_ohlcv(ticker: str) -> OHLCVResponse:
    ticker = normalize_ticker(ticker)
    exchange = _detect_exchange(ticker)

    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1mo")
    except YFRateLimitError:
        raise HTTPException(status_code=429, detail="Rate limited by Yahoo Finance. Please try again in a few seconds.")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch data: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for ticker '{ticker}'. Check that the symbol is valid.")

    records = _df_to_ohlcv_records(df)
    return OHLCVResponse(ticker=ticker, exchange=exchange, records=records)


def get_stock_info(ticker: str) -> StockInfo:
    ticker = normalize_ticker(ticker)

    try:
        stock = yf.Ticker(ticker)
        info = stock.info
    except YFRateLimitError:
        raise HTTPException(status_code=429, detail="Rate limited by Yahoo Finance. Please try again in a few seconds.")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch info: {str(e)}")

    if not info or (
        info.get("regularMarketPrice") is None
        and info.get("currentPrice") is None
        and info.get("previousClose") is None
    ):
        raise HTTPException(status_code=404, detail=f"No info found for ticker '{ticker}'. Check that the symbol is valid.")

    current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")

    return StockInfo(
        ticker=ticker,
        company_name=info.get("longName") or info.get("shortName"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        market_cap=info.get("marketCap"),
        current_price=current_price,
        currency=info.get("currency"),
        exchange=info.get("exchange"),
    )


def get_history(ticker: str, period: str) -> HistoryResponse:
    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period '{period}'. Valid options: {', '.join(sorted(VALID_PERIODS))}",
        )

    ticker = normalize_ticker(ticker)

    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
    except YFRateLimitError:
        raise HTTPException(status_code=429, detail="Rate limited by Yahoo Finance. Please try again in a few seconds.")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch history: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No historical data found for ticker '{ticker}'.")

    records = _df_to_ohlcv_records(df)
    return HistoryResponse(ticker=ticker, period=period, records=records)


def get_indices() -> IndicesResponse:
    symbols = {"nifty50": "^NSEI", "sensex": "^BSESN"}
    names = {"nifty50": "Nifty 50", "sensex": "BSE Sensex"}
    results = {}

    for key, symbol in symbols.items():
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
        except YFRateLimitError:
            raise HTTPException(status_code=429, detail="Rate limited by Yahoo Finance. Please try again in a few seconds.")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch index data: {str(e)}")

        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        current = info.get("currentPrice") or info.get("regularMarketPrice") or prev_close

        change = round(current - prev_close, 2) if current is not None and prev_close is not None else None
        change_pct = round((change / prev_close) * 100, 2) if change is not None and prev_close else None

        results[key] = IndexData(
            name=names[key],
            symbol=symbol,
            current_value=round(current, 2) if current is not None else None,
            previous_close=round(prev_close, 2) if prev_close is not None else None,
            change=change,
            change_pct=change_pct,
        )

    return IndicesResponse(**results)
