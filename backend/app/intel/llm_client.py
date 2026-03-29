"""Groq LLM client wrapper with two-tier model strategy.

- ask_llm()      → openai/gpt-oss-120b  (deep reasoning: extraction, analysis, briefing, Q&A)
- ask_llm_fast() → llama-3.3-70b-versatile  (worker/validation: query gen, relevance check, gap analysis)
"""

import json
import re
import os
from groq import AsyncGroq
from app.config import settings

_client = None

MODEL_DEEP = "openai/gpt-oss-120b"
MODEL_FAST = "llama-3.3-70b-versatile"


def _get_client() -> AsyncGroq:
    """Lazily init the async Groq client."""
    global _client
    if _client is None:
        api_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
        _client = AsyncGroq(api_key=api_key)
    return _client


def _clean_json(text: str) -> str:
    """Strip markdown fences and whitespace before parsing."""
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text.strip()


async def _call(model: str, system_prompt: str, user_prompt: str, temperature: float = 0.4, max_tokens: int = 1500) -> dict | list:
    """Internal: send a chat completion and return parsed JSON.

    Retries **at most 2 times** (1 initial + 1 retry).
    Logs structured GROQ_API_ERROR details on every failure.
    """
    import asyncio
    import logging
    logger = logging.getLogger(__name__)
    client = _get_client()

    MAX_ATTEMPTS = 2
    last_error = None
    # Ensure content is always a plain string (prevents Groq 400 Bad Request)
    system_prompt = str(system_prompt)
    user_prompt = str(user_prompt)

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            return json.loads(_clean_json(content))
        except Exception as e:
            last_error = e
            error_str = str(e)
            logger.error(
                f"GROQ_API_ERROR | model={model} | attempt={attempt+1}/{MAX_ATTEMPTS} | "
                f"type={type(e).__name__} | detail={error_str}"
            )
            if "429" in error_str or "rate_limit" in error_str.lower():
                logger.warning(f"Rate limited. Moving forward without retrying...")
                raise e
            elif attempt < MAX_ATTEMPTS - 1:
                # Non-rate-limit error — still retry once
                await asyncio.sleep(2)
            else:
                raise e
    raise last_error


async def ask_llm(system_prompt: str, user_prompt: str, language: str = "English") -> dict | list:
    """Deep reasoning model (gpt-oss-120b) — for extraction, analysis, briefings, Q&A."""
    if language.lower() != "english":
        system_prompt += f"\n\nCRITICAL INSTRUCTION: Produce all final output (titles, summaries, briefings, and analysis) in {language}."
    return await _call(MODEL_DEEP, system_prompt, user_prompt, temperature=0.3)


async def ask_llm_fast(system_prompt: str, user_prompt: str, language: str = "English") -> dict | list:
    """Fast worker model (llama-3.3-70b) — for query generation, validation, gap checks."""
    if language.lower() != "english":
        system_prompt += f"\n\nCRITICAL INSTRUCTION: Produce all final output (titles, summaries, briefings, and analysis) in {language}. Keep JSON keys strictly in English."
    return await _call(MODEL_FAST, system_prompt, user_prompt, temperature=0.5)


async def transcribe_audio(file_bytes: bytes, filename: str) -> str:
    """Use Groq Whisper to transcribe audio input. Retries at most 2 times."""
    import asyncio
    import logging
    logger = logging.getLogger(__name__)
    client = _get_client()

    MAX_ATTEMPTS = 2
    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = await client.audio.transcriptions.create(
                file=(filename, file_bytes),
                model="whisper-large-v3",
                response_format="json"
            )
            return response.text
        except Exception as e:
            last_error = e
            logger.error(
                f"GROQ_API_ERROR | transcription | attempt={attempt+1}/{MAX_ATTEMPTS} | "
                f"type={type(e).__name__} | detail={str(e)}"
            )
            if "429" in str(e) or "rate_limit" in str(e).lower():
                logger.warning(f"Rate limited. Moving forward without retrying...")
                raise e
            elif attempt < MAX_ATTEMPTS - 1:
                await asyncio.sleep(2)
            else:
                raise e
    raise last_error
