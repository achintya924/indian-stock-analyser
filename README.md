# India Stock Analyser

A FastAPI-based REST API for fetching Indian stock market data from NSE and BSE using `yfinance`.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/stock/{ticker}` | OHLCV data for last 30 days |
| GET | `/stock/{ticker}/info` | Company info (name, sector, market cap, price) |
| GET | `/stock/{ticker}/history?period=1mo` | Historical data with configurable period |
| GET | `/indices` | Nifty 50 and Sensex current values |

## Ticker Formats

- **NSE**: `RELIANCE.NS`, `TCS.NS`, `INFY.NS`
- **BSE**: `500325.BO`, `532540.BO`
- **Auto-suffix**: Pass `RELIANCE` and `.NS` will be appended automatically

## Valid Periods

`1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | India Stock Analyser | Application name |
| `DEBUG` | false | Enable debug mode |
