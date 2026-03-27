from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Create the async database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,   # prints SQL queries — helpful while learning, set False in production
)

# Session factory — use this to talk to the DB
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# All models will inherit from this base class
class Base(DeclarativeBase):
    pass


# ─── Dependency for FastAPI routes ────────────────────────────
# Inject this into any route that needs DB access
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
