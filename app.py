import os
import shutil
import requests
import assemblyai as aai  # Import AssemblyAI
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

# --- Create Uploads Directory (for Day 5 functionality) ---
UPLOADS_DIR = "uploads"
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

# --- API Key Configuration ---
MURF_API_KEY = os.getenv("MURF_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

# Configure AssemblyAI
aai.settings.api_key = ASSEMBLYAI_API_KEY


# Pydantic model for TTS request
class TTSRequest(BaseModel):
    text: str
    voice_id: str = "en-US-natalie"


# --- Frontend Route ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main index.html page."""
    return templates.TemplateResponse("index.html", {"request": request})


# --- TTS API Endpoint (Day 3) ---
@app.post("/generate-audio/")
async def generate_audio(request: TTSRequest):
    # (Code from previous day, no changes needed)
    if not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="Murf API key not found.")
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


# --- Audio Upload Endpoint (Day 5) ---
@app.post("/upload-audio/")
async def upload_audio(audio: UploadFile = File(...)):
    # (Code from previous day, no changes needed)
    file_path = os.path.join(UPLOADS_DIR, audio.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
        file_size = os.path.getsize(file_path)
        return {
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


# --- NEW: Transcription Endpoint (Day 6) ---
@app.post("/transcribe/file")
async def transcribe_file(audio: UploadFile = File(...)):
    """
    Accepts an audio file and returns the transcription.
    """
    if not ASSEMBLYAI_API_KEY:
        raise HTTPException(status_code=500, detail="AssemblyAI API key not found.")

    try:
        # The SDK directly handles the uploaded file object
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio.file)

        if transcript.status == aai.TranscriptStatus.error:
            raise HTTPException(status_code=500, detail=transcript.error)

        if not transcript.text:
            raise HTTPException(
                status_code=400, detail="Empty or invalid audio received."
            )

        return {"transcription": transcript.text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        audio.file.close()
