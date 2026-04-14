import logging
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy import select, update

from app.database import async_session, RawArticle
from app.services.sentiment_service import analyse_sentiment
from app.services.news_service import _strip_exchange_suffix

logger = logging.getLogger(__name__)


@dataclass
class ScoreSummary:
    total_scored: int
    positive_count: int
    negative_count: int
    neutral_count: int


@dataclass
class SentimentAggregation:
    ticker: str
    hours: int
    aggregate_score: float
    total_articles: int
    positive_pct: float
    negative_pct: float
    neutral_pct: float


async def score_articles(ticker: str) -> ScoreSummary:
    """Fetch and score all unscored articles for a ticker."""
    base_ticker = _strip_exchange_suffix(ticker)
    counts = {"positive": 0, "negative": 0, "neutral": 0}

    async with async_session() as session:
        result = await session.execute(
            select(RawArticle)
            .where(RawArticle.ticker == base_ticker)
            .where(RawArticle.sentiment_label.is_(None))
        )
        articles = result.scalars().all()

    for article in articles:
        text = article.title
        if article.content:
            text = f"{article.title}. {article.content}"

        sentiment = analyse_sentiment(text)

        async with async_session() as session:
            await session.execute(
                update(RawArticle)
                .where(RawArticle.id == article.id)
                .values(
                    sentiment_label=sentiment.label,
                    sentiment_score=sentiment.score,
                    sentiment_model=sentiment.model_name,
                    scored_at=datetime.utcnow(),
                )
            )
            await session.commit()

        counts[sentiment.label] += 1

    total = sum(counts.values())
    logger.info("Scored %d articles for %s: %s", total, base_ticker, counts)

    return ScoreSummary(
        total_scored=total,
        positive_count=counts["positive"],
        negative_count=counts["negative"],
        neutral_count=counts["neutral"],
    )


async def fetch_sentiment_summary(ticker: str, hours: int = 24) -> SentimentAggregation:
    """Pull all articles scored in the last N hours and compute a weighted aggregate."""
    base_ticker = _strip_exchange_suffix(ticker)
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    async with async_session() as session:
        result = await session.execute(
            select(RawArticle)
            .where(RawArticle.ticker == base_ticker)
            .where(RawArticle.sentiment_label.isnot(None))
            .where(RawArticle.scored_at >= cutoff)
        )
        articles = result.scalars().all()

    total = len(articles)
    if total == 0:
        return SentimentAggregation(
            ticker=base_ticker,
            hours=hours,
            aggregate_score=0.0,
            total_articles=0,
            positive_pct=0.0,
            negative_pct=0.0,
            neutral_pct=0.0,
        )

    weighted_sum = 0.0
    pos = neg = neu = 0

    for article in articles:
        score = article.sentiment_score or 0.0
        if article.sentiment_label == "positive":
            weighted_sum += 1.0 * score
            pos += 1
        elif article.sentiment_label == "negative":
            weighted_sum += -1.0 * score
            neg += 1
        else:
            neu += 1

    aggregate = round(weighted_sum / total, 4)

    return SentimentAggregation(
        ticker=base_ticker,
        hours=hours,
        aggregate_score=aggregate,
        total_articles=total,
        positive_pct=round((pos / total) * 100, 2),
        negative_pct=round((neg / total) * 100, 2),
        neutral_pct=round((neu / total) * 100, 2),
    )
