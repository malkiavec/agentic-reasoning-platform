import os
from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://agent:agent@postgres:5432/agentic"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings=DatabaseSettings()
pool_kwargs={"pool_pre_ping":True}
if os.getenv("APP_ENV","production").lower() in {"test","testing"}:
    pool_kwargs["poolclass"]=NullPool
engine=create_async_engine(settings.database_url,**pool_kwargs)
SessionLocal=async_sessionmaker(engine,expire_on_commit=False)

async def session_scope()->AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
