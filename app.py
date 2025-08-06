import os
import shutil
import requests
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# --- CORS Middleware Setup ---
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Template and Static File Setup ---
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Create Uploads Directory ---
UPLOADS_DIR = "uploads"
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)


# Pydantic model for TTS request
class TTSRequest(BaseModel):
    text: str
    voice_id: str = "en-US-natalie"


# Murf API configuration
MURF_API_URL = "https://api.murf.ai/v1/speech/generate"
MURF_API_KEY = os.getenv("MURF_API_KEY")


# --- Frontend Route ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main index.html page."""
    return templates.TemplateResponse("index.html", {"request": request})


# --- TTS API Endpoint ---
@app.post("/generate-audio/")
async def generate_audio(request: TTSRequest):
    """Calls the Murf TTS API and returns the audio URL."""
    if not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="API key not found.")

    headers = {"Content-Type": "application/json", "api-key": MURF_API_KEY}
    payload = {"text": request.text, "voiceId": request.voice_id, "format": "MP3"}

    try:
        response = requests.post(MURF_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        audio_url = data.get("audioFile")
        if not audio_url:
            raise HTTPException(
                status_code=500, detail="Audio URL not found in Murf API response."
            )
        return {"audio_url": audio_url}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error calling Murf API: {e}")


# --- NEW: Audio Upload Endpoint ---
@app.post("/upload-audio/")
async def upload_audio(audio: UploadFile = File(...)):
    """
    Receives an audio file, saves it, and returns its details.
    """
    if not audio:
        raise HTTPException(status_code=400, detail="No audio file sent.")

    # Define the file path
    file_path = os.path.join(UPLOADS_DIR, audio.filename)

    try:
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)

        # Get file size
        file_size = os.path.getsize(file_path)

        return {
            "message": "File uploaded successfully!",
            "filename": audio.filename,
            "content_type": audio.content_type,
            "size_in_bytes": file_size,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"There was an error uploading the file: {e}"
        )
    finally:
        audio.file.close()
