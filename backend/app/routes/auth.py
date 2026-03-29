"""Auth routes — Clerk-based profile management."""

import json
import base64
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.models.user import User
from app.clerk_auth import get_clerk_user_id
from app.services.redis_service import redis_client
from app.intel.llm_client import transcribe_audio, ask_llm_fast, ask_llm
from app.pipeline.voice_generator import generate_quick_audio

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class ProfileUpdateRequest(BaseModel):
    interests: Optional[List[str]] = None
    level: Optional[str] = None
    role: Optional[str] = None
    preferred_language: Optional[str] = None


class ProfileSetupRequest(BaseModel):
    role: str = "student"
    interests: List[str] = []
    level: str = "beginner"
    preferred_language: str = "English"


def cache_user_profile(user: User):
    """Save user profile in Redis for fast access during personalization."""
    import json
    profile = {
        "id": user.id,
        "clerk_id": user.clerk_id,
        "role": user.role,
        "interests": user.interests or [],
        "level": user.level,
        "engagement": user.engagement or {},
        "preferred_language": user.preferred_language or "English",
    }
    redis_client.setex(f"user:{user.id}", 86400, json.dumps(profile))
    if user.clerk_id:
        redis_client.setex(f"clerk_user:{user.clerk_id}", 86400, str(user.id))


async def get_or_create_user(clerk_id: str, db: AsyncSession) -> User:
    """Get existing user by Clerk ID or create a new one."""
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(clerk_id=clerk_id, role="student", interests=[], level="beginner", engagement={}, preferred_language="English")
        db.add(user)
        await db.flush()
        await db.commit()
        cache_user_profile(user)

    return user


@router.get("/profile")
async def get_profile(
    clerk_id: str = Depends(get_clerk_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's profile."""
    user = await get_or_create_user(clerk_id, db)
    return {
        "id": user.id,
        "clerk_id": user.clerk_id,
        "email": user.email,
        "role": user.role,
        "interests": user.interests,
        "level": user.level,
        "engagement": user.engagement,
        "preferred_language": user.preferred_language or "English",
        "needs_setup": not user.interests,
        "REQUIRED_ONBOARDING": not user.interests,
    }


@router.post("/profile/setup")
async def setup_profile(
    body: ProfileSetupRequest,
    clerk_id: str = Depends(get_clerk_user_id),
    db: AsyncSession = Depends(get_db),
):
    """First-time profile setup after Clerk login."""
    user = await get_or_create_user(clerk_id, db)
    user.role = body.role
    user.interests = body.interests
    user.level = body.level
    user.preferred_language = body.preferred_language
    await db.commit()
    cache_user_profile(user)
    return {"message": "Profile configured", "user_id": user.id}


@router.put("/profile")
async def update_profile(
    body: ProfileUpdateRequest,
    clerk_id: str = Depends(get_clerk_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update user preferences."""
    user = await get_or_create_user(clerk_id, db)

    if body.interests is not None:
        user.interests = body.interests
    if body.level is not None:
        user.level = body.level
    if body.role is not None:
        user.role = body.role
    if body.preferred_language is not None:
        user.preferred_language = body.preferred_language

    await db.commit()
    cache_user_profile(user)
    redis_client.delete(f"feed:{user.id}")

    return {"message": "Profile updated", "user_id": user.id}


@router.post("/profile/voice-onboarding")
async def voice_onboarding(
    audio: UploadFile = File(...),
    clerk_id: str = Depends(get_clerk_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update user preferences via voice onboarding."""
    user = await get_or_create_user(clerk_id, db)

    # 1. Transcribe audio
    try:
        file_bytes = await audio.read()
        transcript = await transcribe_audio(file_bytes, audio.filename or "audio.webm")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    if not transcript.strip():
        raise HTTPException(status_code=400, detail="Voice audio was empty or unintelligible.")

    # 2. Extract profile data
    system_prompt = """You are an onboarding assistant for a highly personalized news platform.
Extract the user's 'role' (e.g. student, investor, founder), 'level' (beginner, intermediate, advanced), and a list of 'interests'.
The text will be a transcription of the user's voice talking about themselves.
Return strict JSON with the fields:
{"role": "string", "level": "string", "interests": ["string", "string"]}
Default missing items: role='student', level='beginner', interests=['General News'].
"""
    try:
        extracted = await ask_llm_fast(system_prompt, f"Transcript:\n{transcript}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM extraction failed: {str(e)}")

    # 3. Update Profile
    user.role = extracted.get("role", "student").lower()
    user.level = extracted.get("level", "beginner").lower()
    user.interests = extracted.get("interests", ["General News"])

    await db.commit()
    cache_user_profile(user)
    redis_client.delete(f"feed:{user.id}")

    return {
        "message": "Profile configured via voice",
        "user_id": user.id,
        "transcript": transcript,
        "extracted": extracted
    }


@router.post("/interview/next")
async def interview_next(
    state: str = Form(...),
    audio: Optional[UploadFile] = File(None),
    clerk_id: str = Depends(get_clerk_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Multi-turn bidirectional voice onboarding endpoint."""
    user = await get_or_create_user(clerk_id, db)
    
    # Parse state
    try:
        state_data = json.loads(state)
        history = state_data.get("history", [])
        role = state_data.get("role", "student")
        level = state_data.get("level", "beginner")
        interests = state_data.get("interests", [])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid state JSON")

    # 1. Transcribe audio if provided
    transcript = ""
    if audio:
        try:
            file_bytes = await audio.read()
            if file_bytes:
                transcript = await transcribe_audio(file_bytes, audio.filename or "audio.webm")
                history.append({"role": "user", "content": transcript})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    # 2. Check if we have complete info & generate next question
    system_prompt = """You are an interactive AI voice interviewer collecting user preferences.
The goal is to determine the user's 'role' (e.g. student, founder, investor), 'level' (beginner, intermediate, advanced directly mapping to their role), and a robust set of 'interests' (at least 3 specific news topics like Crypto, AI, Fintech, etc.).

Analyze the conversation so far. Can you confidently extract ALL of these properties based on the conversation history?
Return strict JSON:
{
  "complete": boolean,
  "missing_info": "Explain briefly what is missing to guide your next question",
  "next_question": "A concise, natural-sounding, single follow-up question. (Empty if complete is true)",
  "extracted": {
     "role": "string (or null if not known)",
     "level": "string (or null if not known)",
     "interests": ["list", "of", "strings"]
  }
}"""

    # Format history for LLM
    history_text = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
    user_prompt = f"Current extracted knowledge:\nRole: {role}\nLevel: {level}\nInterests: {interests}\n\nConversation History:\n{history_text}"

    try:
        analysis = await ask_llm(system_prompt, user_prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM extraction failed: {str(e)}")

    is_complete = analysis.get("complete", False)
    extracted = analysis.get("extracted", {})

    if is_complete and extracted.get("role") and len(extracted.get("interests", [])) >= 3:
        # Save complete profile
        user.role = extracted.get("role", "student").lower()
        user.level = extracted.get("level", "beginner").lower()
        user.interests = extracted.get("interests", [])
        await db.commit()
        cache_user_profile(user)
        redis_client.delete(f"feed:{user.id}")

        return {
            "status": "COMPLETE",
            "extracted": extracted,
            "transcript": transcript,
            "history": history
        }
    
    # 3. Not complete, ask next question
    next_q = analysis.get("next_question", "Could you tell me a bit more about your background and interests?")
    if not next_q.strip():
        next_q = "Could you tell me what specific topics you want to read about?"

    history.append({"role": "assistant", "content": next_q})

    # Generate Voice
    try:
        audio_bytes = generate_quick_audio(next_q, voice_id="pMsXgVXv3BLzUgSXRplE") # Serena
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")

    return {
        "status": "CONTINUE",
        "question": next_q,
        "audio_base64": audio_base64,
        "transcript": transcript,
        "history": history,
        "extracted": extracted
    }
