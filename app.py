import os
import requests
import assemblyai as aai
import google.generativeai as genai
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

# Initialize FastAPI app
app = FastAPI()

# CORS Setup
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Template and static files setup
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load API keys from environment
MURF_API_KEY = os.getenv("MURF_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure AssemblyAI and Gemini API
aai.settings.api_key = ASSEMBLYAI_API_KEY
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Murf client
murf = Murf(api_key=MURF_API_KEY)


# Pydantic model for text requests (can be used by other endpoints)
class TTSRequest(BaseModel):
    text: str
    voice_id: str = "en-US-natalie"


# Frontend route
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# Existing Text-to-Speech endpoint (Day 3)
@app.post("/generate-audio/")
async def generate_audio(request: TTSRequest):
    if not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="Murf API key not configured.")
    try:
        api_response = murf.text_to_speech.generate(
            text=request.text, voice_id=request.voice_id
        )
        return {"audio_url": api_response.audio_file}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling Murf API: {e}")


# --- UPDATED /llm/query endpoint to accept audio input (Day 9) ---
@app.post("/llm/query")
async def llm_query(audio: UploadFile = File(...)):
    if not (GEMINI_API_KEY and ASSEMBLYAI_API_KEY and MURF_API_KEY):
        raise HTTPException(
            status_code=500, detail="One or more API keys are not configured."
        )

    try:
        # 1. Transcribe the audio with AssemblyAI
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio.file)

        if transcript.status == aai.TranscriptStatus.error:
            raise HTTPException(
                status_code=500, detail=f"Transcription failed: {transcript.error}"
            )
        if not transcript.text:
            raise HTTPException(status_code=400, detail="Could not understand audio.")

        # 2. Generate LLM response via Gemini API
        model = genai.GenerativeModel("gemini-1.5-flash")
        llm_response = model.generate_content(transcript.text)

        # 3. Handle character limit for Murf API (max 3000 chars)
        llm_text = llm_response.text.strip()
        max_chars = 3000

        # If response > 3000 chars, truncate or split (here, we truncate)
        if len(llm_text) > max_chars:
            llm_text = llm_text[:max_chars]

        # 4. Generate speech audio for LLM response using Murf
        murf_response = murf.text_to_speech.generate(
            text=llm_text,
            voice_id="en-US-natalie",  # You can change the voice as needed
        )

        # Return the audio url to the client
        return {"audio_url": murf_response.audio_file}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if audio and not audio.file.closed:
            audio.file.close()
