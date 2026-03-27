from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://etuser:etpassword@postgres:5432/et_newsroom"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Auth
    SECRET_KEY: str = "supersecretkey123"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Groq
    GROQ_API_KEY: str | None = None

    # News
    NEWS_FETCH_INTERVAL_MINUTES: int = 15
    MAX_ARTICLES_PER_FEED: int = 10

    class Config:
        env_file = ".env"        # reads your .env file automatically


# One global settings object — import this everywhere
settings = Settings()
