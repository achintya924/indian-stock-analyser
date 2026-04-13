import logging
import os
from datetime import datetime

import tweepy
from sqlalchemy.exc import IntegrityError

from app.database import async_session, RawArticle
from app.services.news_service import _strip_exchange_suffix, TICKER_COMPANY_MAP

logger = logging.getLogger(__name__)


def _get_client() -> tweepy.Client | None:
    """Create a Tweepy v2 client from the bearer token, or return None if not configured."""
    token = os.getenv("TWITTER_BEARER_TOKEN", "").strip()
    if not token:
        logger.warning("TWITTER_BEARER_TOKEN not set — skipping Twitter scrape")
        return None
    return tweepy.Client(bearer_token=token, wait_on_rate_limit=True)


async def scrape_tweets(ticker: str) -> int:
    """Search recent tweets for the given ticker. Returns count of new tweets saved."""
    client = _get_client()
    if client is None:
        return 0

    base_ticker = _strip_exchange_suffix(ticker)

    # Build query: cashtag first, company name as fallback
    cashtag_query = f"${base_ticker} -is:retweet lang:en"
    company_name = TICKER_COMPANY_MAP.get(base_ticker)
    company_query = f"{company_name} stock -is:retweet lang:en" if company_name else None

    saved = 0

    for query in filter(None, [cashtag_query, company_query]):
        try:
            response = client.search_recent_tweets(
                query=query,
                max_results=50,
                tweet_fields=["created_at", "text", "author_id"],
            )
        except tweepy.errors.TweepyException as e:
            logger.warning("Twitter search failed for query '%s': %s", query, e)
            continue

        if not response.data:
            continue

        for tweet in response.data:
            tweet_url = f"https://twitter.com/i/status/{tweet.id}"
            published = tweet.created_at if tweet.created_at else datetime.utcnow()

            article = RawArticle(
                ticker=base_ticker,
                source="twitter",
                title=tweet.text[:500],
                url=tweet_url,
                content=tweet.text,
                published_at=published,
            )

            async with async_session() as session:
                try:
                    session.add(article)
                    await session.commit()
                    saved += 1
                except IntegrityError:
                    await session.rollback()

    logger.info("Twitter scrape for %s: saved %d new tweets", base_ticker, saved)
    return saved
