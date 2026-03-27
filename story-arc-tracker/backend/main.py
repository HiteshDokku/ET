"""Story Arc Tracker — FastAPI Application."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import StoryRequest, StoryArcResponse
from services.aggregator import analyze_story

app = FastAPI(
    title="Story Arc Tracker",
    description="Transform news articles into structured, interactive story arcs.",
    version="1.0.0",
)

# CORS — allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def health_check():
    return {"status": "ok", "service": "Story Arc Tracker"}


@app.post("/analyze", response_model=StoryArcResponse)
async def analyze(request: StoryRequest):
    """Analyze articles and return a structured story arc."""
    if not request.articles:
        raise HTTPException(status_code=400, detail="At least one article is required.")
    if not request.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")

    try:
        result = await analyze_story(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
