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
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Validate API Keys at startup
if not MURF_API_KEY:
    logger.warning("Missing API key: MURF_API_KEY")
if not ASSEMBLYAI_API_KEY:
    logger.warning("Missing API key: ASSEMBLYAI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("Missing API key: GEMINI_API_KEY")

# Configure APIs
if ASSEMBLYAI_API_KEY:
    aai.settings.api_key = ASSEMBLYAI_API_KEY
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
if MURF_API_KEY:
    murf = Murf(api_key=MURF_API_KEY)

# --- In-Memory Datastore for Chat History ---
chat_histories = {}

# --- Error Response Templates ---
ERROR_RESPONSES = {
    "stt_error": "I'm having trouble hearing you right now. Could you please try again?",
    "llm_error": "I'm having trouble thinking right now. Please give me a moment and try again.",
    "api_key_error": "My services aren't configured correctly. Please contact support.",
    "general_error": "Something unexpected happened. Please try again in a moment.",
}


# --- Utility Function for Fallback Audio ---
def create_fallback_audio_response(error_message: str):
    """Attempts to create a fallback audio response using TTS."""
    if not MURF_API_KEY:
        return {"error": True, "message": error_message, "audio_url": None}

    try:
        api_response = murf.text_to_speech.generate(
            text=error_message, voice_id="en-US-natalie"
        )
        return {
            "error": True,
            "message": error_message,
            "audio_url": api_response.audio_file,
        }
    except Exception as e:
        logger.error(f"Fallback TTS failed: {str(e)}")
        return {"error": True, "message": error_message, "audio_url": None}


# --- Frontend Route ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main index.html page."""
    return templates.TemplateResponse("index.html", {"request": request})


# --- Robust Conversational Agent Endpoint ---
@app.post("/agent/chat/{session_id}")
async def agent_chat(session_id: str, audio: UploadFile = File(...)):
    """
    Handles a full conversational turn with error handling:
    Audio (user) -> STT -> History -> LLM -> History -> TTS -> Audio (bot)
    """
    logger.info(f"Processing chat request for session: {session_id}")
    # --- START OF DAY 24 CHANGE ---

    # Define the agent's persona
    AGENT_PERSONA = (
        "You are 'Botto', a witty, slightly sassy robot assistant. "
        "You are helpful, but you always end your answers with a clever, "
        "sarcastic joke or a funny observation about humans. "
        "Keep your answers super concise and to the point, but don't forget the sass."
    )

    # --- END OF DAY 24 CHANGE ---
    # Check for API key availability
    if not ASSEMBLYAI_API_KEY or not GEMINI_API_KEY or not MURF_API_KEY:
        logger.error("One or more API keys are not configured.")
        return create_fallback_audio_response(ERROR_RESPONSES["api_key_error"])

    try:
        # 1. TRANSCRIPTION PHASE
        logger.info("Starting transcription...")
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio.file)

        if transcript.status == aai.TranscriptStatus.error:
            logger.error(f"STT Error: {transcript.error}")
            return create_fallback_audio_response(ERROR_RESPONSES["stt_error"])

        if not transcript.text or transcript.text.strip() == "":
            logger.warning("STT returned empty transcript.")
            return create_fallback_audio_response(
                "I didn't catch that. Could you please speak clearly?"
            )

        user_message = transcript.text.strip()
        logger.info(f"Transcription successful: {user_message[:50]}...")

        # 2. CHAT HISTORY MANAGEMENT
        session_history = chat_histories.get(session_id, [])
        session_history.append({"role": "user", "parts": [user_message]})

        # 3. LLM RESPONSE GENERATION
        logger.info("Generating LLM response...")
        model = genai.GenerativeModel(
            "gemini-2.5-flash-lite", system_instruction=AGENT_PERSONA
        )

        # Start chat with history (excluding the latest user message)
        chat_session = model.start_chat(history=session_history[:-1])
        # Send the latest user message
        llm_response = chat_session.send_message(session_history[-1])

        llm_text = llm_response.text.strip()
        logger.info(f"LLM response generated: {llm_text[:50]}...")

        # Update chat history with LLM response
        session_history.append({"role": "model", "parts": [llm_text]})
        chat_histories[session_id] = session_history

        # 4. TEXT-TO-SPEECH GENERATION
        logger.info("Generating TTS response...")

        # Handle Murf's 3000 character limit
        if len(llm_text) > 3000:
            llm_text = (
                llm_text[:2950] + "... I have more to say, but I'll keep it brief."
            )
            logger.warning("LLM response truncated for TTS.")

        murf_response = murf.text_to_speech.generate(
            text=llm_text, voice_id="en-US-natalie"  # You can change this voice
        )

        logger.info("TTS generation successful.")
        return {"audio_url": murf_response.audio_file, "error": False}

    except Exception as e:
        logger.error(f"Unexpected error in agent_chat: {str(e)}")
        return create_fallback_audio_response(ERROR_RESPONSES["general_error"])
    finally:
        try:
            if audio and hasattr(audio, "file") and not audio.file.closed:
                audio.file.close()
        except Exception as e:
            logger.error(f"Error closing audio file: {str(e)}")
