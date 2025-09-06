"""
Database connection and session management
"""
import os
from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from supabase import create_client, Client

from app.core.config import get_settings
from app.models.database import Base

settings = get_settings()

# Database engines
if settings.database_url:
    # Use direct PostgreSQL connection if provided
    if settings.database_url.startswith("postgresql://"):
        # Convert to async URL for SQLAlchemy
        async_database_url = settings.database_url.replace(
            "postgresql://", "postgresql+asyncpg://"
        )
    else:
        async_database_url = settings.database_url
    
    # Async engine for SQLAlchemy operations
    async_engine = create_async_engine(
        async_database_url,
        echo=settings.debug,
        future=True
    )
    
    # Sync engine for migrations and initial setup
    sync_engine = create_engine(
        settings.database_url,
        echo=settings.debug,
        future=True
    )
else:
    # Extract database connection info from Supabase URL
    # This is a simplified approach - in production, you'd want more robust URL parsing
    supabase_host = settings.supabase_url.replace("https://", "").replace("http://", "")
    database_url = f"postgresql://postgres:[YOUR_DB_PASSWORD]@db.{supabase_host}:5432/postgres"
    
    async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    async_engine = create_async_engine(
        async_database_url,
        echo=settings.debug,
        future=True
    )
    
    sync_engine = create_engine(
        database_url,
        echo=settings.debug,
        future=True
    )

# Session makers
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

# Supabase client
supabase_client: Client = create_client(
    settings.supabase_url,
    settings.supabase_anon_key
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session() -> Session:
    """Get sync database session for migrations"""
    session = SessionLocal()
    try:
        return session
    finally:
        session.close()


async def init_db():
    """Initialize database tables"""
    async with async_engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    await async_engine.dispose()


def get_supabase_client() -> Client:
    """Get Supabase client"""
    return supabase_client