import logging
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

DATABASE_URL = "sqlite+aiosqlite:///india_stock.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class RawArticle(Base):
    __tablename__ = "raw_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(50), nullable=False, index=True)
    source = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    url = Column(Text, nullable=False, unique=True)
    content = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Phase 3: sentiment columns
    sentiment_label = Column(String(20), nullable=True)
    sentiment_score = Column(Float, nullable=True)
    sentiment_model = Column(String(20), nullable=True)
    scored_at = Column(DateTime, nullable=True)


def _migrate_sentiment_columns(conn):
    """Add sentiment columns to existing raw_articles table if they don't exist."""
    result = conn.execute(text("PRAGMA table_info(raw_articles)"))
    existing_cols = {row[1] for row in result.fetchall()}

    new_columns = {
        "sentiment_label": "VARCHAR(20)",
        "sentiment_score": "FLOAT",
        "sentiment_model": "VARCHAR(20)",
        "scored_at": "DATETIME",
    }

    for col_name, col_type in new_columns.items():
        if col_name not in existing_cols:
            conn.execute(text(f"ALTER TABLE raw_articles ADD COLUMN {col_name} {col_type}"))
            logger.info("Added column '%s' to raw_articles", col_name)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(lambda sync_conn: _migrate_sentiment_columns(sync_conn))
