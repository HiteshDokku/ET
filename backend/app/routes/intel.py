"""Intelligence hub routes — News Navigator and Story Arc endpoints."""

import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.intel import StoryArcResponse
from app.intel.aggregator import analyze_story
from app.intel.scraping_agent import ScrapingAgent
from app.intel.briefing_service import generate_briefing
from app.intel.llm_client import ask_llm
from app.models.intel import StoryRequest

router = APIRouter(prefix="/api/intel", tags=["Intelligence Hub"])

class TopicRequest(BaseModel):
    topic: str


class AskRequest(BaseModel):
    question: str
    context: str = ""


@router.post("/generate")
async def generate_briefing_endpoint(req: TopicRequest):
    """News Navigator: Scraping Agent → Briefing → Follow-ups."""

    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")

    try:
        agent = ScrapingAgent(req.topic)
        curated_articles = await agent.run()

        if not curated_articles:
            return {
                "briefing": {
                    "Summary": "No articles found for this topic.",
                    "Key Insights": ["Try another topic or broaden your search."],
                    "Market Impact": "N/A",
                    "Controversies / Concerns": "N/A",
                    "What To Watch": "N/A",
                },
                "followups": [],
                "articles": [],
            }

        articles_as_dicts = [a.model_dump() for a in curated_articles]
        result = await generate_briefing(articles_as_dicts)

        return {
            "briefing": result.get("briefing", {}),
            "followups": result.get("followups", []),
            "articles": articles_as_dicts,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/generate-arc", response_model=StoryArcResponse)
async def generate_arc_endpoint(req: TopicRequest):
    """Story Arc: Scraping Agent → Full Analysis Pipeline."""

    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")

    try:
        agent = ScrapingAgent(req.topic)
        curated_articles = await agent.run()

        if not curated_articles:
            raise HTTPException(status_code=404, detail="No articles found for this topic.")

        story_request = StoryRequest(topic=req.topic, articles=curated_articles)
        result = await analyze_story(story_request)
        result.articles = curated_articles

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/ask")
async def ask_question(req: AskRequest):
    """Follow-up Q&A based on last generated context."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if not req.context.strip():
        raise HTTPException(status_code=400, detail="No context available. Generate a briefing or story arc first.")

    system_prompt = """You are an Economic Times financial analyst.
Answer clearly and concisely based only on the provided information.
When referring to the source of your information, use phrases like "According to the articles" instead of "According to the briefing".
Return your answer as a JSON object: {"answer": "your detailed answer here"}"""

    user_prompt = f"""Here is the information from the analyzed articles:

{req.context}

User question:
{req.question}"""

    try:
        result = await ask_llm(system_prompt, user_prompt)
        answer = result.get("answer", str(result))
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Q&A failed: {str(e)}")
