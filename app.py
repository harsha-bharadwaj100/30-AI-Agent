import os
import shutil
import requests
import assemblyai as aai
import google.generativeai as genai  # Import Google GenAI
from murf.client import Murf
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

# --- API Key and SDK Configuration ---
MURF_API_KEY = os.getenv("MURF_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # New Gemini Key

# Configure AssemblyAI
aai.settings.api_key = ASSEMBLYAI_API_KEY

# Initialize Murf SDK client
murf = Murf(api_key=MURF_API_KEY)

# Configure Google GenAI
genai.configure(api_key=GEMINI_API_KEY)


# --- Pydantic Models ---
class TTSRequest(BaseModel):
    text: str
    voice_id: str = "en-US-natalie"


# NEW: Pydantic model for LLM query
class LLMQueryRequest(BaseModel):
    text: str


# --- Frontend Route ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main index.html page."""
    return templates.TemplateResponse("index.html", {"request": request})


# --- Text-to-Speech Endpoint (Day 3) ---
@app.post("/generate-audio/")
async def generate_audio(request: TTSRequest):
    if not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="Murf API key not found.")
    try:
        api_response = murf.text_to_speech.generate(
            text=request.text, voice_id=request.voice_id
        )
        return {"audio_url": api_response.audio_file}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling Murf API: {e}")


# --- Echo Bot v2 Endpoint (Day 7) ---
@app.post("/tts/echo")
async def tts_echo(audio: UploadFile = File(...)):
    """
    Receives audio, transcribes it, generates speech from the transcript,
    and returns the new audio URL.
    """
    if not ASSEMBLYAI_API_KEY or not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="API key(s) not configured.")

    try:
        # 1. Transcribe the incoming audio
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio.file)

        if transcript.status == aai.TranscriptStatus.error:
            raise HTTPException(
                status_code=500, detail=f"Transcription failed: {transcript.error}"
            )

        if not transcript.text:
            raise HTTPException(status_code=400, detail="Could not understand audio.")

        api_response = murf.text_to_speech.generate(
            text=transcript.text, voice_id="en-US-terrell"
        )
        return {"audio_url": api_response.audio_file}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if audio and not audio.file.closed:
            audio.file.close()


# --- NEW: LLM Query Endpoint (Day 8) ---
@app.post("/llm/query")
async def llm_query(request: LLMQueryRequest):
    """
    Accepts text, sends it to the Gemini LLM, and returns the response.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured.")

    if not request.text:
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    try:
        # Initialize the Gemini Pro model
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Generate content
        response = model.generate_content(request.text)

        return {"response": response.text}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred with the Gemini API: {str(e)}"
        )
