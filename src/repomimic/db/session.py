

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)
from src.repomimic.settings import get_settings

settings = get_settings()
_engine = create_async_engine(settings.DATABASE_URL)
SessionMaker = async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)