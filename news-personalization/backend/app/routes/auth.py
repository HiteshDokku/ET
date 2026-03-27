from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.config import settings
from app.services.redis_service import redis_client

router = APIRouter(prefix="/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Request / Response Schemas (what JSON looks like) ────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    role: str          = "student"     # student | investor | founder
    interests: List[str] = []           # ["AI", "startups", "crypto"]
    level: str         = "beginner"    # beginner | intermediate | expert

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ProfileUpdateRequest(BaseModel):
    interests: Optional[List[str]] = None
    level: Optional[str]           = None
    role: Optional[str]            = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str


# ─── Helper functions ─────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(user_id: int) -> str:
    """Create a JWT token that expires after settings.ACCESS_TOKEN_EXPIRE_MINUTES"""
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def cache_user_profile(user: User):
    """Save user profile in Redis for fast access during personalization"""
    profile = {
        "id":        user.id,
        "role":      user.role,
        "interests": user.interests or [],
        "level":     user.level,
        "engagement": user.engagement or {},
    }
    # Store in Redis with key "user:{id}" — expires after 24 hours
    redis_client.setex(f"user:{user.id}", 86400, str(profile))


# ─── Routes ───────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user.
    Stores profile in both PostgreSQL (permanent) and Redis (fast cache).
    """
    # Check if email already registered
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user in DB
    user = User(
        email           = body.email,
        hashed_password = hash_password(body.password),
        role            = body.role,
        interests       = body.interests,
        level           = body.level,
        engagement      = {},
    )
    db.add(user)
    await db.flush()   # get user.id without committing yet
    await db.commit()  # COMMIT to database

    # Cache profile in Redis for fast personalization
    cache_user_profile(user)

    token = create_token(user.id)
    return TokenResponse(access_token=token, user_id=user.id, role=user.role)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email + password. Returns a JWT token."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    # Refresh Redis cache on login
    cache_user_profile(user)

    token = create_token(user.id)
    return TokenResponse(access_token=token, user_id=user.id, role=user.role)


@router.put("/profile/{user_id}")
async def update_profile(
    user_id: int,
    body: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Update user preferences.
    Called when user changes their interests or role.
    Also invalidates the Redis cache so next feed is regenerated fresh.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.interests is not None:
        user.interests = body.interests
    if body.level is not None:
        user.level = body.level
    if body.role is not None:
        user.role = body.role

    await db.commit()  # COMMIT changes to database

    # Update Redis cache
    cache_user_profile(user)

    # Delete old cached feed so it regenerates with new preferences
    redis_client.delete(f"feed:{user_id}")

    return {"message": "Profile updated", "user_id": user_id}


@router.get("/profile/{user_id}")
async def get_profile(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get a user's profile."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id":        user.id,
        "email":     user.email,
        "role":      user.role,
        "interests": user.interests,
        "level":     user.level,
        "engagement": user.engagement,
    }
