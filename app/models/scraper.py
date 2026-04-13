from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ScrapeResult(BaseModel):
    ticker: str
    news_count: int
    twitter_count: int
    total: int


class ArticleOut(BaseModel):
    id: int
    ticker: str
    source: str
    title: str
    url: str
    content: Optional[str]
    published_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class ArticlesResponse(BaseModel):
    ticker: str
    count: int
    articles: list[ArticleOut]
