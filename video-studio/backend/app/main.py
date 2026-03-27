"""FastAPI application for AI News Video Agent Pro."""

import uuid
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.models import JobRequest, JobResponse, JobStatus, JobState
from app.tasks import generate_video_task, get_job_status

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI News Video Agent Pro",
    description="Generate broadcast-quality AI news videos from topics",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount output directory for video serving
import os
os.makedirs(settings.output_dir, exist_ok=True)
app.mount("/output", StaticFiles(directory=settings.output_dir), name="output")


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "AI News Video Agent Pro"}


@app.post("/api/generate", response_model=JobResponse)
async def generate_video(request: JobRequest):
    """Submit a video generation job."""
    job_id = str(uuid.uuid4())

    # Validate API keys are configured
    if not settings.groq_api_key:
        raise HTTPException(400, "GROQ_API_KEY not configured")
    if not settings.elevenlabs_api_key:
        raise HTTPException(400, "ELEVENLABS_API_KEY not configured")
    if not settings.pexels_api_key:
        raise HTTPException(400, "PEXELS_API_KEY not configured")

    logger.info(f"New job {job_id}: {request.topic}")

    # Submit to Celery
    generate_video_task.delay(
        job_id=job_id,
        topic=request.topic,
        source_url=request.source_url,
        voice_id=request.voice_id,
    )

    return JobResponse(
        job_id=job_id,
        status=JobState.QUEUED,
        message=f"Job queued for processing: {request.topic}",
    )


@app.get("/api/status/{job_id}", response_model=JobStatus)
async def job_status(job_id: str):
    """Get the status of a video generation job."""
    data = get_job_status(job_id)
    if not data:
        raise HTTPException(404, f"Job {job_id} not found")

    return JobStatus(
        job_id=data["job_id"],
        status=JobState(data["status"]),
        progress=data.get("progress", 0.0),
        current_stage=data.get("current_stage", ""),
        message=data.get("message", ""),
        video_url=data.get("video_url") or None,
        qa_report=data.get("qa_report"),
        iteration=data.get("iteration", 0),
        error=data.get("error") or None,
    )


@app.get("/api/download/{job_id}")
async def download_video(job_id: str):
    """Download the generated video."""
    data = get_job_status(job_id)
    if not data:
        raise HTTPException(404, f"Job {job_id} not found")
    if data["status"] != JobState.COMPLETED.value:
        raise HTTPException(400, "Video not ready yet")

    video_path = os.path.join(settings.output_dir, job_id, "final.mp4")
    if not os.path.exists(video_path):
        raise HTTPException(404, "Video file not found")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"news_video_{job_id[:8]}.mp4",
    )
