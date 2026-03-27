"""Unified Pipeline — FastAPI Application."""

import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from models import StoryRequest, StoryArcResponse, ArticleInput
from services.aggregator import analyze_story
from services.scraping_agent import ScrapingAgent
from services.gemma_api import generate_briefing
from services.llm_client import ask_llm

app = FastAPI(
    title="ET Unified Intelligence Pipeline",
    description="News Navigator Briefings & Story Arc Analysis — powered by an agentic scraping engine.",
    version="2.0.0",
)

# CORS — allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared state for follow-up Q&A ───────────────────────────
last_context = ""


# ── Request Models ────────────────────────────────────────────

class TopicRequest(BaseModel):
    topic: str


class AskRequest(BaseModel):
    question: str


# ── Routes ────────────────────────────────────────────────────

@app.get("/")
async def health_check():
    return {"status": "ok", "service": "ET Unified Intelligence Pipeline"}


@app.post("/generate")
async def generate_briefing_endpoint(req: TopicRequest):
    """
    News Navigator Pipeline:
    ScrapingAgent → generate_briefing() → Briefing JSON + followups
    """
    global last_context

    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")

    try:
        # Step 1: Run the Scraping Agent
        agent = ScrapingAgent(req.topic)
        curated_articles = await agent.run()

        if not curated_articles:
            return {
                "briefing": {
                    "Summary": "No articles found for this topic.",
                    "Key Insights": ["Try another topic or broaden your search."],
                    "Market Impact": "N/A",
                    "Controversies / Concerns": "N/A",
                    "What To Watch": "N/A"
                },
                "followups": [],
                "articles": []
            }

        # Convert ArticleInput models to dicts for the briefing generator
        articles_as_dicts = [a.model_dump() for a in curated_articles]

        # Step 2: Generate briefing
        result = await generate_briefing(articles_as_dicts)

        # Store context for follow-up Q&A
        if isinstance(result.get("briefing"), dict):
            last_context = json.dumps(result["briefing"], indent=2)
        else:
            last_context = str(result.get("briefing", ""))

        return {
            "briefing": result.get("briefing", {}),
            "followups": result.get("followups", []),
            "articles": articles_as_dicts
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.post("/generate-arc", response_model=StoryArcResponse)
async def generate_arc_endpoint(req: TopicRequest):
    """
    Story Arc Pipeline:
    ScrapingAgent → analyze_story() → StoryArcResponse
    """
    global last_context

    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")

    try:
        # Step 1: Run the Scraping Agent
        agent = ScrapingAgent(req.topic)
        curated_articles = await agent.run()

        if not curated_articles:
            raise HTTPException(status_code=404, detail="No articles found for this topic.")

        # Step 2: Wrap and pass to the story arc aggregator
        story_request = StoryRequest(topic=req.topic, articles=curated_articles)
        result = await analyze_story(story_request)

        # Attach the source articles to the response
        result.articles = curated_articles

        # Store context for follow-up Q&A
        last_context = result.story_summary

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/ask")
async def ask_question(req: AskRequest):
    """Follow-up Q&A based on the last generated briefing or story arc."""
    global last_context

    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if not last_context:
        raise HTTPException(status_code=400, detail="No context available. Generate a briefing or story arc first.")

    system_prompt = """You are an Economic Times financial analyst.
Answer clearly and concisely based only on the provided information.
When referring to the source of your information, use phrases like "According to the articles" instead of "According to the briefing".
Return your answer as a JSON object: {"answer": "your detailed answer here"}"""

    user_prompt = f"""Here is the information from the analyzed articles:

{last_context}

User question:
{req.question}"""

    try:
        result = await ask_llm(system_prompt, user_prompt)
        answer = result.get("answer", str(result))
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Q&A failed: {str(e)}")
