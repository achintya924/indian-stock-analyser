import logging

from fastapi import APIRouter, HTTPException, Query

from app.models.sentiment import ScoreResponse, SentimentSummaryResponse
from app.services.scoring_service import score_articles, fetch_sentiment_summary

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sentiment/{ticker}/score", response_model=ScoreResponse)
async def score_ticker(ticker: str):
    """Score all unscored articles for the given ticker."""
    try:
        summary = await score_articles(ticker)
    except Exception as e:
        logger.error("Scoring failed for %s: %s", ticker, e)
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")

    return ScoreResponse(
        ticker=summary.total_scored and ticker.upper().split(".")[0] or ticker.upper().split(".")[0],
        total_scored=summary.total_scored,
        positive_count=summary.positive_count,
        negative_count=summary.negative_count,
        neutral_count=summary.neutral_count,
    )


@router.get("/sentiment/{ticker}", response_model=SentimentSummaryResponse)
async def get_sentiment(
    ticker: str,
    hours: int = Query(default=24, ge=1, le=720, description="Lookback window in hours"),
):
    """Return aggregate sentiment summary for the given ticker over the past N hours."""
    try:
        agg = await fetch_sentiment_summary(ticker, hours=hours)
    except Exception as e:
        logger.error("Sentiment fetch failed for %s: %s", ticker, e)
        raise HTTPException(status_code=500, detail=f"Sentiment fetch failed: {str(e)}")

    return SentimentSummaryResponse(
        ticker=agg.ticker,
        hours=agg.hours,
        aggregate_score=agg.aggregate_score,
        total_articles=agg.total_articles,
        positive_pct=agg.positive_pct,
        negative_pct=agg.negative_pct,
        neutral_pct=agg.neutral_pct,
    )
