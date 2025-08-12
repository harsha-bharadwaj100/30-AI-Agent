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
missing_keys = []
if not MURF_API_KEY:
    missing_keys.append("MURF_API_KEY")
if not ASSEMBLYAI_API_KEY:
    missing_keys.append("ASSEMBLYAI_API_KEY")
if not GEMINI_API_KEY:
    missing_keys.append("GEMINI_API_KEY")

if missing_keys:
    logger.warning(f"Missing API keys: {', '.join(missing_keys)}")

# Configure APIs only if keys are present
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
    "tts_error": "I'm having trouble speaking right now. Let me try a different approach.",
    "api_key_error": "I'm having configuration issues. Please contact support.",
    "network_error": "I'm having trouble connecting right now. Please check your connection and try again.",
    "general_error": "Something unexpected happened. Please try again in a moment.",
}


# --- Pydantic Models ---
class TTSRequest(BaseModel):
    text: str


class LLMQueryRequest(BaseModel):
    text: str


# --- Utility Functions for Error Handling ---
def create_fallback_audio_response(error_message: str):
    """
    Attempts to create a fallback audio response using TTS.
    If TTS fails, returns a text-only response.
    """
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


def handle_stt_error(error):
    """Handle STT-specific errors with appropriate fallbacks."""
    logger.error(f"STT Error: {str(error)}")
    if "api key" in str(error).lower() or "unauthorized" in str(error).lower():
        return create_fallback_audio_response(ERROR_RESPONSES["api_key_error"])
    elif "network" in str(error).lower() or "connection" in str(error).lower():
        return create_fallback_audio_response(ERROR_RESPONSES["network_error"])
    else:
        return create_fallback_audio_response(ERROR_RESPONSES["stt_error"])


def handle_llm_error(error):
    """Handle LLM-specific errors with appropriate fallbacks."""
    logger.error(f"LLM Error: {str(error)}")
    if "api key" in str(error).lower() or "unauthorized" in str(error).lower():
        return create_fallback_audio_response(ERROR_RESPONSES["api_key_error"])
    elif "quota" in str(error).lower() or "limit" in str(error).lower():
        return create_fallback_audio_response(
            "I've reached my thinking limit for now. Please try again later."
        )
    else:
        return create_fallback_audio_response(ERROR_RESPONSES["llm_error"])


def handle_tts_error(error, text_response):
    """Handle TTS-specific errors with text fallback."""
    logger.error(f"TTS Error: {str(error)}")
    return {
        "error": True,
        "message": f"Audio generation failed, but here's my response: {text_response}",
        "audio_url": None,
    }


# --- Frontend Route ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main index.html page."""
    return templates.TemplateResponse("index.html", {"request": request})


# --- Robust Conversational Agent Endpoint (Day 11) ---
@app.post("/agent/chat/{session_id}")
async def agent_chat(session_id: str, audio: UploadFile = File(...)):
    """
    Handles a full conversational turn with comprehensive error handling:
    Audio (user) -> STT -> Append to History -> LLM -> Append to History -> TTS -> Audio (bot)
    """
    logger.info(f"Processing chat request for session: {session_id}")

    try:
        # Validate audio file
        if not audio or not audio.file:
            raise HTTPException(status_code=400, detail="No audio file provided")

        # Check for API key availability
        if not ASSEMBLYAI_API_KEY:
            logger.error("AssemblyAI API key not configured")
            return create_fallback_audio_response(ERROR_RESPONSES["api_key_error"])

        if not GEMINI_API_KEY:
            logger.error("Gemini API key not configured")
            return create_fallback_audio_response(ERROR_RESPONSES["api_key_error"])

        # 1. TRANSCRIPTION PHASE with error handling
        try:
            logger.info("Starting transcription...")
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(audio.file)

            if transcript.status == aai.TranscriptStatus.error:
                return handle_stt_error(f"Transcription failed: {transcript.error}")

            if not transcript.text or transcript.text.strip() == "":
                return create_fallback_audio_response(
                    "I didn't catch that. Could you please speak more clearly?"
                )

            user_message = transcript.text.strip()
            logger.info(f"Transcription successful: {user_message[:50]}...")

        except Exception as e:
            logger.error(f"STT Exception: {str(e)}")
            return handle_stt_error(e)

        # 2. CHAT HISTORY MANAGEMENT with error handling
        try:
            session_history = chat_histories.get(session_id, [])
            session_history.append({"role": "user", "parts": [user_message]})
            logger.info(f"Updated chat history for session {session_id}")
        except Exception as e:
            logger.error(f"Chat history error: {str(e)}")
            # Continue without history if there's an issue
            session_history = [{"role": "user", "parts": [user_message]}]

        # 3. LLM RESPONSE GENERATION with error handling
        try:
            logger.info("Generating LLM response...")
            model = genai.GenerativeModel("gemini-1.5-flash")

            if len(session_history) > 1:
                chat_session = model.start_chat(history=session_history[:-1])
                llm_response = chat_session.send_message(
                    session_history[-1]["parts"][0]
                )
            else:
                llm_response = model.generate_content(user_message)

            if not llm_response or not llm_response.text:
                return handle_llm_error("Empty response from LLM")

            llm_text = llm_response.text.strip()
            logger.info(f"LLM response generated successfully: {llm_text[:50]}...")

            # Update chat history with LLM response
            session_history.append({"role": "model", "parts": [llm_text]})
            chat_histories[session_id] = session_history

        except Exception as e:
            logger.error(f"LLM Exception: {str(e)}")
            return handle_llm_error(e)

        # 4. TEXT-TO-SPEECH GENERATION with error handling
        if not MURF_API_KEY:
            logger.error("Murf API key not configured")
            return {
                "error": True,
                "message": f"Text response only: {llm_text}",
                "audio_url": None,
            }

        try:
            logger.info("Generating TTS response...")

            # Handle character limit for Murf API (max 3000 chars)
            if len(llm_text) > 3000:
                llm_text = (
                    llm_text[:2950]
                    + "... I have more to say, but I'll keep it brief for now."
                )
                logger.warning("LLM response truncated due to TTS character limit")

            murf_response = murf.text_to_speech.generate(
                text=llm_text, voice_id="en-US-natalie"
            )

            logger.info("TTS generation successful")
            return {"audio_url": murf_response.audio_file}

        except Exception as e:
            logger.error(f"TTS Exception: {str(e)}")
            return handle_tts_error(e, llm_text)

    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in agent_chat: {str(e)}")
        return create_fallback_audio_response(ERROR_RESPONSES["general_error"])
    finally:
        # Always ensure the audio file is properly closed
        try:
            if audio and hasattr(audio, "file") and not audio.file.closed:
                audio.file.close()
        except Exception as e:
            logger.error(f"Error closing audio file: {str(e)}")


# --- Health Check Endpoint ---
@app.get("/health")
async def health_check():
    """Health check endpoint to verify API connectivity."""
    status = {
        "status": "healthy",
        "apis": {
            "assemblyai": bool(ASSEMBLYAI_API_KEY),
            "gemini": bool(GEMINI_API_KEY),
            "murf": bool(MURF_API_KEY),
        },
    }

    # Test API connectivity if keys are present
    warnings = []

    if not ASSEMBLYAI_API_KEY:
        warnings.append("AssemblyAI API key missing")
    if not GEMINI_API_KEY:
        warnings.append("Gemini API key missing")
    if not MURF_API_KEY:
        warnings.append("Murf API key missing")

    if warnings:
        status["warnings"] = warnings
        status["status"] = "degraded"

    return status
