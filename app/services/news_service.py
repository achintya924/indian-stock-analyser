import logging
from datetime import datetime
from time import mktime

import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import async_session, RawArticle

logger = logging.getLogger(__name__)

RSS_FEEDS = {
    "Economic Times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Moneycontrol": "https://www.moneycontrol.com/rss/marketsindia.xml",
    "Business Standard": "https://www.business-standard.com/rss/markets-106.rss",
    "Mint Markets": "https://www.livemint.com/rss/markets",
}

# Common ticker → company name mapping for Indian stocks
TICKER_COMPANY_MAP = {
    "RELIANCE": "Reliance",
    "TCS": "TCS",
    "INFY": "Infosys",
    "HDFCBANK": "HDFC Bank",
    "ICICIBANK": "ICICI Bank",
    "HINDUNILVR": "Hindustan Unilever",
    "ITC": "ITC",
    "SBIN": "SBI",
    "BHARTIARTL": "Bharti Airtel",
    "KOTAKBANK": "Kotak Mahindra",
    "LT": "Larsen",
    "AXISBANK": "Axis Bank",
    "WIPRO": "Wipro",
    "HCLTECH": "HCL Tech",
    "TATAMOTORS": "Tata Motors",
    "TATASTEEL": "Tata Steel",
    "ADANIENT": "Adani Enterprises",
    "ADANIPORTS": "Adani Ports",
    "BAJFINANCE": "Bajaj Finance",
    "MARUTI": "Maruti",
    "NIFTY": "Nifty",
    "SENSEX": "Sensex",
}


def _strip_exchange_suffix(ticker: str) -> str:
    """Remove .NS or .BO suffix to get the base ticker."""
    ticker = ticker.upper()
    for suffix in (".NS", ".BO"):
        if ticker.endswith(suffix):
            return ticker[: -len(suffix)]
    return ticker


def _build_search_terms(ticker: str) -> list[str]:
    """Build a list of search terms for matching headlines."""
    base = _strip_exchange_suffix(ticker)
    terms = [base.lower()]
    company_name = TICKER_COMPANY_MAP.get(base)
    if company_name:
        terms.append(company_name.lower())
    return terms


def _matches(text: str, search_terms: list[str]) -> bool:
    """Check if any search term appears in the text."""
    text_lower = text.lower()
    return any(term in text_lower for term in search_terms)


def _parse_published(entry) -> datetime | None:
    """Extract published datetime from a feed entry."""
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                return datetime.fromtimestamp(mktime(parsed))
            except (ValueError, OverflowError):
                continue
    return None


async def scrape_news(ticker: str) -> int:
    """Scrape RSS feeds for articles matching the ticker. Returns count of new articles saved."""
    search_terms = _build_search_terms(ticker)
    base_ticker = _strip_exchange_suffix(ticker)
    saved = 0

    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": "IndiaStockAnalyser/1.0"},
    ) as client:
        for source_name, feed_url in RSS_FEEDS.items():
            try:
                resp = await client.get(feed_url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.warning("Failed to fetch %s (%s): %s", source_name, feed_url, e)
                continue

            feed = feedparser.parse(resp.text)

            for entry in feed.entries:
                title = getattr(entry, "title", "") or ""
                summary = getattr(entry, "summary", "") or ""
                link = getattr(entry, "link", "") or ""

                if not link or not title:
                    continue

                if not _matches(title, search_terms) and not _matches(summary, search_terms):
                    continue

                published = _parse_published(entry)

                article = RawArticle(
                    ticker=base_ticker,
                    source=source_name,
                    title=title.strip(),
                    url=link.strip(),
                    content=summary.strip() or None,
                    published_at=published,
                )

                async with async_session() as session:
                    try:
                        session.add(article)
                        await session.commit()
                        saved += 1
                    except IntegrityError:
                        await session.rollback()
                        # Duplicate URL — already stored

    logger.info("News scrape for %s: saved %d new articles", base_ticker, saved)
    return saved
