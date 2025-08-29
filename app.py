import os
import asyncio
import uuid
import assemblyai as aai
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# --- Setup ---
load_dotenv()
app = FastAPI()

# --- Static and Template Files Setup ---
# This ensures your server can find your HTML and JS files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create an uploads folder if it doesn't exist (from Day 16)
UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)


# --- API Key Configuration ---
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
if not ASSEMBLYAI_API_KEY:
    print("Warning: ASSEMBLYAI_API_KEY environment variable not set.")
else:
    aai.settings.api_key = ASSEMBLYAI_API_KEY


# --- THIS IS THE MISSING PART ---
# Add this endpoint to serve your index.html file
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    Serves the main index.html page.
    """
    return templates.TemplateResponse("index.html", {"request": request})


# --- END OF MISSING PART ---


# --- WebSocket Handler for Day 17 ---
@app.websocket("/ws/stream-for-transcription")
async def websocket_stream_transcription(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection accepted.")

    transcript_buffer = []

    async def on_data(transcript):
        # Called every time AssemblyAI has a piece of transcription
        print("Transcript update:", transcript.text)
        transcript_buffer.append(transcript.text)

    async def on_error(error):
        print("AssemblyAI streaming error:", error)

    # Setup the real-time transcriber
    transcriber = aai.RealtimeTranscriber(
        sample_rate=16000,
        encoding="pcm_s16le",  # PCM 16-bit little-endian
        # channels=1,
        on_data=on_data,
        on_error=on_error,
    )

    # Use a context manager to manage the transcriber's websocket session
    with transcriber:
        print("Connected to AssemblyAI websocket for transcription...")
        try:
            while True:
                chunk = websocket.receive_bytes()
                transcriber.send(chunk)
        except WebSocketDisconnect:
            print("WebSocket client disconnected.")
        finally:
            transcriber.close()
