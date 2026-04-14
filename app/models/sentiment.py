from pydantic import BaseModel


class ScoreResponse(BaseModel):
    ticker: str
    total_scored: int
    positive_count: int
    negative_count: int
    neutral_count: int


class SentimentSummaryResponse(BaseModel):
    ticker: str
    hours: int
    aggregate_score: float
    total_articles: int
    positive_pct: float
    negative_pct: float
    neutral_pct: float
