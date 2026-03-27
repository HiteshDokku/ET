"""Google Gemini LLM client wrapper for structured JSON responses."""

import json
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

_client = None
MODEL = "gemini-2.5-flash"


def _get_client():
    """Lazily init the Gemini client."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client


async def ask_llm(system_prompt: str, user_prompt: str) -> dict | list:
    """Send a prompt to Gemini and return parsed JSON."""
    client = _get_client()
    response = await client.aio.models.generate_content(
        model=MODEL,
        contents=user_prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0.4,
        ),
    )
    content = response.text
    return json.loads(content)
