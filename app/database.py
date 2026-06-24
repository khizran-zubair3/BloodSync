import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# Database Connection URL (Defaults to a placeholder Neon URL or environment variable)
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://neondb_owner:npg_ErxNj8bPOR6G@ep-polished-sound-aq89y7xn-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"
)

# Automatically adapt standard postgresql URL to asyncpg driver if needed
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Strip sslmode/channel_binding query params for asyncpg compatibility and use connect_args
if "?" in DATABASE_URL:
    clean_db_url = DATABASE_URL.split("?")[0]
else:
    clean_db_url = DATABASE_URL

# Async Engine for Neon / PostgreSQL with explicit SSL parameter
engine = create_async_engine(
    clean_db_url, 
    connect_args={"ssl": True}, 
    pool_pre_ping=True,
    pool_recycle=300,
    echo=True, 
    future=True
)

# Async Session Factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Dependency to get db session in FastAPI routes
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
