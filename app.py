import os
import shutil
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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

aai.settings.api_key = ASSEMBLYAI_API_KEY
genai.configure(api_key=GEMINI_API_KEY)
murf = Murf(api_key=MURF_API_KEY)

# --- In-Memory Datastore for Chat History ---
# NOTE: This is a simple dictionary for prototyping.
# In a production environment, this would be a database (e.g., Redis, PostgreSQL).
# This will be cleared every time the server restarts.
chat_histories = {}


# --- Pydantic Models (can be kept for other endpoints) ---
class TTSRequest(BaseModel):
    text: str


class LLMQueryRequest(BaseModel):
    text: str


# --- Frontend Route ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main index.html page."""
    return templates.TemplateResponse("index.html", {"request": request})


# --- NEW: Conversational Agent Endpoint (Day 10) ---
@app.post("/agent/chat/{session_id}")
async def agent_chat(session_id: str, audio: UploadFile = File(...)):
    """
    Handles a full conversational turn:
    Audio (user) -> STT -> Append to History -> LLM -> Append to History -> TTS -> Audio (bot)
    """
    if not (GEMINI_API_KEY and ASSEMBLYAI_API_KEY and MURF_API_KEY):
        raise HTTPException(
            status_code=500, detail="One or more API keys are not configured."
        )

    try:
        # 1. Transcribe audio to text with AssemblyAI
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio.file)

        if transcript.status == aai.TranscriptStatus.error:
            raise HTTPException(
                status_code=500, detail=f"Transcription failed: {transcript.error}"
            )
        if not transcript.text:
            raise HTTPException(status_code=400, detail="Could not understand audio.")

        # 2. Retrieve or initialize chat history for the session
        session_history = chat_histories.get(session_id, [])
        session_history.append({"role": "user", "parts": [transcript.text]})

        # 3. Generate LLM response with history via Gemini API
        model = genai.GenerativeModel("gemini-1.5-flash")
        # The Gemini API expects the history in this format
        chat_session = model.start_chat(history=session_history[:-1])
        llm_response = chat_session.send_message(session_history[-1])

        llm_text = llm_response.text.strip()

        # 4. Append LLM's response to the history
        session_history.append({"role": "model", "parts": [llm_text]})
        chat_histories[session_id] = session_history

        # 5. Handle character limit for Murf API (max 3000 chars)
        if len(llm_text) > 3000:
            llm_text = llm_text[:3000]

        # 6. Generate speech audio for LLM response using Murf
        murf_response = murf.text_to_speech.generate(
            text=llm_text,
            voice_id="en-US-natalie",  # Using Natalie's voice for the agent
        )

        return {"audio_url": murf_response.audio_file}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if audio and not audio.file.closed:
            audio.file.close()
