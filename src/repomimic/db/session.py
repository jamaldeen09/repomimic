

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)
from src.repomimic.settings import get_settings

settings = get_settings()
_engine = create_async_engine(settings.DATABASE_URL)

def get_session_factory () -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)

async def create_db_session (): 
    async with get_session_factory() as session:
        yield session