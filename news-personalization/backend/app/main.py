from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routes import auth, news
from app.config import settings


# ─── Startup / Shutdown logic ─────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup: creates DB tables if they don't exist.
    Runs on shutdown: closes DB connections.
    """
    print("🚀 Starting My ET Backend...")

    # Create all database tables automatically
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables ready")

    # Trigger first news fetch immediately on startup
    try:
        from app.celery_app.celery_config import fetch_and_cache_news
        fetch_and_cache_news.delay()   # .delay() = run as background task
        print("📰 Triggered initial news fetch via Celery")
    except Exception as e:
        print(f"⚠️  Could not trigger Celery task: {e}")

    yield  # app runs here

    print("🛑 Shutting down My ET Backend...")
    await engine.dispose()


# ─── Create FastAPI app ───────────────────────────────────────
app = FastAPI(
    title="My ET — Personalized Newsroom API",
    description="""
    Backend for the AI-native personalized newsroom.

    - Students get explainer-first news
    - Investors get market analysis
    - Founders get startup ecosystem angles

    The system learns from every interaction to get smarter over time.
    """,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow frontend (localhost:5500)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Register routes ──────────────────────────────────────────
app.include_router(auth.router)
app.include_router(news.router)


# ─── Health check ─────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "running",
        "app": "My ET Personalized Newsroom",
        "docs": "/docs",   # Swagger UI is auto-generated at /docs
    }

@app.get("/health", tags=["Health"])
async def health():
    """Check if Redis and DB are reachable."""
    from app.services.redis_service import redis_client

    redis_ok = False
    try:
        redis_client.ping()
        redis_ok = True
    except Exception:
        pass

    return {
        "api":   "ok",
        "redis": "ok" if redis_ok else "unreachable",
    }
