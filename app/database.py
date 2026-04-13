from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

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


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
