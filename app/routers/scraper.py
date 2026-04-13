from fastapi import APIRouter
from sqlalchemy import select

from app.database import async_session, RawArticle
from app.models.scraper import ScrapeResult, ArticleOut, ArticlesResponse
from app.services.news_service import scrape_news, _strip_exchange_suffix
from app.services import twitter_service

router = APIRouter()


@router.post("/scrape/{ticker}", response_model=ScrapeResult)
async def trigger_scrape(ticker: str):
    """Triggers news RSS and Twitter scrape for the given ticker."""
    news_count = await scrape_news(ticker)
    twitter_count = await twitter_service.scrape_tweets(ticker)

    base_ticker = _strip_exchange_suffix(ticker)
    return ScrapeResult(
        ticker=base_ticker,
        news_count=news_count,
        twitter_count=twitter_count,
        total=news_count + twitter_count,
    )


@router.get("/scrape/{ticker}/articles", response_model=ArticlesResponse)
async def get_articles(ticker: str):
    """Returns last 50 stored articles for the ticker, newest first."""
    base_ticker = _strip_exchange_suffix(ticker)

    async with async_session() as session:
        result = await session.execute(
            select(RawArticle)
            .where(RawArticle.ticker == base_ticker)
            .order_by(RawArticle.published_at.desc().nullslast())
            .limit(50)
        )
        rows = result.scalars().all()

    articles = [ArticleOut.model_validate(row) for row in rows]
    return ArticlesResponse(ticker=base_ticker, count=len(articles), articles=articles)
