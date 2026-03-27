from sqlalchemy import Column, Integer, String, JSON, DateTime, func
from app.database import Base

class User(Base):
    """
    Stores every registered user.
    The 'profile' column is a JSON blob — flexible, no schema changes needed.
    """
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # ─── Personalization fields ──────────────────────────────
    # role: "student" | "investor" | "founder"
    role          = Column(String, default="student")

    # interests: list stored as JSON, e.g. ["AI", "startups", "crypto"]
    interests     = Column(JSON, default=list)

    # level: "beginner" | "intermediate" | "expert"
    level         = Column(String, default="beginner")

    # engagement: tracks what user actually clicks/reads
    # e.g. {"AI": 0.9, "politics": 0.1}
    engagement    = Column(JSON, default=dict)

    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class Article(Base):
    """
    Stores fetched news articles (raw, before personalization).
    Celery fills this table every 15 minutes.
    """
    __tablename__ = "articles"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String, nullable=False)
    summary     = Column(String)
    url         = Column(String, unique=True)
    source      = Column(String)          # e.g. "ET Markets", "ET Tech"
    category    = Column(String)          # e.g. "markets", "startups", "AI"
    published   = Column(DateTime(timezone=True))
    fetched_at  = Column(DateTime(timezone=True), server_default=func.now())
