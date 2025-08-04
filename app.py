import os
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware  # Import CORS
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# --- CORS Middleware Setup ---
# This allows your frontend (even on a different origin) to communicate with this backend.
origins = ["*"]  # For development, allow all origins. For production, restrict this.

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- End CORS Setup ---

# --- Template and Static File Setup ---
# To serve the HTML and JS files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
# --- End Template Setup ---


# Pydantic model for the request body
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


# --- API Endpoint ---
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
