import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="AI News Video Studio")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure temp directory exists and mount it to serve generated videos
os.makedirs("assets/temp", exist_ok=True)
app.mount("/videos", StaticFiles(directory="assets/temp"), name="videos")

class VideoRequest(BaseModel):
    article: str

@app.post("/generate-video")
async def generate_video(request: VideoRequest):
    if not request.article.strip():
        raise HTTPException(status_code=400, detail="Article text is required")
    
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "YOUR_API_KEY_HERE":
            raise HTTPException(status_code=500, detail="API Key is missing or invalid.")
            
        from pipeline import generate_video_pipeline
        video_filename = generate_video_pipeline(request.article)
        return {"video_url": f"videos/{video_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
