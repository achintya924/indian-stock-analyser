import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from dotenv import load_dotenv

from app.routers import stock
from app.routers import scraper
from app.routers import sentiment
from app.models.stock import HealthResponse
from app.database import init_db

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "India Stock Analyser")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=APP_NAME,
    description="REST API for Indian stock market data (NSE & BSE) powered by yfinance.",
    version="3.0.0",
    debug=DEBUG,
    lifespan=lifespan,
)

app.include_router(stock.router, tags=["Stocks & Indices"])
app.include_router(scraper.router, tags=["Scraper"])
app.include_router(sentiment.router, tags=["Sentiment"])


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok", app_name=APP_NAME, debug=DEBUG)
