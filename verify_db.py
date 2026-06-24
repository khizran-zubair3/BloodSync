import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://neondb_owner:npg_ErxNj8bPOR6G@ep-polished-sound-aq89y7xn-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"
)

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

if "?" in DATABASE_URL:
    clean_db_url = DATABASE_URL.split("?")[0]
else:
    clean_db_url = DATABASE_URL

tables = [
    "blood_types", "users", "donor_categories", "donors", "staff",
    "hospitals", "hospital_departments", "appointments", "donation_events",
    "donation_histories", "blood_stock", "inventory_logs", "blood_requests",
    "notifications", "equipment", "blood_tests"
]

async def check():
    engine = create_async_engine(clean_db_url, connect_args={"ssl": True})
    async with engine.connect() as conn:
        for t in tables:
            try:
                res = await conn.execute(text(f"SELECT COUNT(*) FROM {t}"))
                count = res.scalar()
                print(f"{t}: {count} rows")
            except Exception as e:
                print(f"{t}: ERROR - {e}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
