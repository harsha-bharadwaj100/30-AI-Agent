import os
import shutil
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Import services
from services.assemblyai_service import AssemblyAIService
from services.murf_service import MurfService
from services.gemini_service import GeminiService  # Import Gemini service

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="AI Voice Agent Backend",
    description="Backend for the 30 Days AI Voice Agent project, featuring STT, TTS, and LLM integration.",
    version="0.1.0",
)

# --- CORS Middleware Setup ---
origins = ["*"]  # For development, allow all origins.
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

# --- Initialize Services ---
# API keys are retrieved from environment variables
try:
    murf_service = MurfService(api_key=os.getenv("MURF_API_KEY"))
    assemblyai_service = AssemblyAIService(api_key=os.getenv("ASSEMBLYAI_API_KEY"))
    gemini_service = GeminiService(api_key=os.getenv("GEMINI_API_KEY"))
except ValueError as e:
    logger.error(f"Failed to initialize service due to missing API key: {e}")
    # In a production app, you might want to stop startup or provide a fallback.
    # For this challenge, we'll let the HTTPException handle it at endpoint level.


# --- Pydantic Models for Request/Response ---
class GenerateAudioRequest(BaseModel):
    text: str = Field(
        ..., min_length=1, max_length=500, description="Text to convert to speech."
    )
    voice_id: str = Field(
        "en-US-natalie", description="Murf AI voice ID to use for speech generation."
    )


class AudioURLResponse(BaseModel):
    audio_url: str = Field(..., description="URL of the generated audio file.")


class TranscriptionResponse(BaseModel):
    transcription: str = Field(..., description="The transcribed text from the audio.")


class EchoBotAudioRequest(BaseModel):
    # This model isn't directly used for UploadFile, but for documentation consistency.
    # FastAPI handles UploadFile directly for form data.
    audio: UploadFile


# --- Frontend Route ---
@app.get("/", response_class=HTMLResponse, summary="Serve Web Interface")
async def read_root(request: Request):
    """
    Serves the main `index.html` web interface for the AI Voice Agent.
    """
    logger.info("Serving index.html")
    return templates.TemplateResponse("index.html", {"request": request})


# --- Text-to-Speech Endpoint ---
@app.post(
    "/generate-audio/",
    response_model=AudioURLResponse,
    summary="Generate Speech from Text",
    description="Converts provided text into an audio file using Murf AI and returns its URL.",
)
async def generate_audio(request_body: GenerateAudioRequest):
    """
    Handles the conversion of text to speech.
    - `request_body`: Contains the text and optionally a voice ID.
    """
    logger.info(
        f"Received request to generate audio for text: {request_body.text[:50]}..."
    )
    try:
        audio_url = murf_service.generate_speech(
            text=request_body.text, voice_id=request_body.voice_id
        )
        return AudioURLResponse(audio_url=audio_url)
    except HTTPException as e:
        logger.error(f"Error generating audio: {e.detail}")
        raise e
    except Exception as e:
        logger.exception("Unexpected error in generate_audio endpoint:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


# --- Echo Bot v2 Endpoint ---
@app.post(
    "/tts/echo",
    response_model=AudioURLResponse,
    summary="Echo Audio in Murf AI Voice",
    description="Receives an audio file, transcribes it, and then generates and returns audio of the transcription using Murf AI.",
)
async def tts_echo(
    audio: UploadFile = File(..., description="Audio file to be echoed.")
):
    """
    Processes an incoming audio file:
    1. Transcribes the audio using AssemblyAI.
    2. Generates new speech from the transcription using Murf AI.
    3. Returns the URL of the new audio.
    """
    logger.info(
        f"Received audio file for echo: {audio.filename}, content_type: {audio.content_type}"
    )
    try:
        # Transcribe the incoming audio
        transcript_text = assemblyai_service.transcribe_audio(audio.file)

        if not transcript_text:
            logger.warning("No clear transcription obtained for echo bot.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not understand audio or received empty audio.",
            )

        logger.info(f"Transcription for echo: {transcript_text[:50]}...")

        # Generate new audio from the transcript using Murf
        echo_audio_url = murf_service.generate_speech(
            text=transcript_text, voice_id="en-US-terrell"  # Or choose another voice
        )

        return AudioURLResponse(audio_url=echo_audio_url)

    except HTTPException as e:
        logger.error(f"Error in tts_echo endpoint: {e.detail}")
        raise e
    except Exception as e:
        logger.exception("Unexpected error in tts_echo endpoint:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )
    finally:
        # Ensure the uploaded file is closed
        if audio and not audio.file.closed:
            audio.file.close()


# --- Placeholder for future LLM interaction endpoint (e.g., chat) ---
@app.post(
    "/chat/",
    summary="Chat with AI Agent",
    description="Sends text to the LLM and gets a text response.",
)
async def chat_with_agent(text_input: str):  # This would typically be a Pydantic model
    logger.info(f"Received chat request: {text_input[:50]}...")
    try:
        response_text = gemini_service.get_chat_response(text_input)
        return {"response": response_text}
    except HTTPException as e:
        logger.error(f"Error chatting with agent: {e.detail}")
        raise e
    except Exception as e:
        logger.exception("Unexpected error in chat_with_agent endpoint:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


# --- Cleanup endpoint for Day 5 (optional, removed if not needed) ---
@app.post(
    "/upload-audio/", include_in_schema=False
)  # Exclude from docs if only for legacy
async def upload_audio_legacy(audio: UploadFile = File(...)):
    """
    (Legacy) Receives an audio file and saves it temporarily.
    This endpoint is maintained for historical context but can be removed
    if the /transcribe/file endpoint fully replaces its purpose.
    """
    UPLOADS_DIR = "uploads"
    if not os.path.exists(UPLOADS_DIR):
        os.makedirs(UPLOADS_DIR)

    file_path = os.path.join(UPLOADS_DIR, audio.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
        file_size = os.path.getsize(file_path)
        logger.info(
            f"Legacy upload successful: {audio.filename}, size: {file_size} bytes"
        )
        return {
            "filename": audio.filename,
            "content_type": audio.content_type,
            "size_in_bytes": file_size,
        }
    except Exception as e:
        logger.exception("Error during legacy audio upload:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}",
        )
    finally:
        if audio and not audio.file.closed:
            audio.file.close()


# --- Transcription Endpoint (Day 6 - Maintained for clarity, though /tts/echo uses similar logic) ---
@app.post(
    "/transcribe/file",
    response_model=TranscriptionResponse,
    summary="Transcribe Audio File",
    description="Transcribes an uploaded audio file using AssemblyAI.",
)
async def transcribe_file_endpoint(
    audio: UploadFile = File(..., description="Audio file to transcribe.")
):
    logger.info(
        f"Received audio file for transcription: {audio.filename}, content_type: {audio.content_type}"
    )
    try:
        transcript_text = assemblyai_service.transcribe_audio(audio.file)
        return TranscriptionResponse(transcription=transcript_text)
    except HTTPException as e:
        logger.error(f"Error transcribing file: {e.detail}")
        raise e
    except Exception as e:
        logger.exception("Unexpected error in transcribe_file_endpoint:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )
    finally:
        if audio and not audio.file.closed:
            audio.file.close()
