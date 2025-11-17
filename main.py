import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Video

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "AI Video Backend Running"}

class GeneratePreviewRequest(BaseModel):
    prompt: str

@app.post("/api/generate-preview")
def generate_preview(payload: GeneratePreviewRequest):
    """
    Creates a Video record with status=preview and a placeholder preview image.
    In a real system you'd call an image generation model here.
    """
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    # For demo: create a simple placeholder image via dummyimage
    # Encode prompt for URL display text (limited)
    text = (prompt[:40] + "...") if len(prompt) > 40 else prompt
    placeholder = f"https://dummyimage.com/1024x576/111827/ffffff&text={text.replace(' ', '+')}"

    video = Video(prompt=prompt, preview_image_url=placeholder, status="preview")
    inserted_id = create_document("video", video)
    return {"id": inserted_id, "preview_image_url": placeholder, "status": "preview"}

class StartVideoRequest(BaseModel):
    video_id: str

@app.post("/api/start-video")
def start_video(payload: StartVideoRequest):
    """
    Simulates background video generation after subscription. 
    In production you'd enqueue a job and update when ready.
    Here we'll immediately mark as ready with a stock sample.
    """
    vid = payload.video_id
    if not vid:
        raise HTTPException(status_code=400, detail="video_id is required")

    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    try:
        _id = ObjectId(vid)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid video_id")

    doc = db["video"].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Video not found")

    # Simulate generated video URL (public sample)
    sample_video = "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4"

    db["video"].update_one(
        {"_id": _id},
        {"$set": {"status": "ready", "video_url": sample_video}}
    )

    updated = db["video"].find_one({"_id": _id})
    updated["id"] = str(updated.pop("_id"))
    return updated

@app.get("/api/videos")
def list_videos(limit: int = 50):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    docs = get_documents("video", {}, limit)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
