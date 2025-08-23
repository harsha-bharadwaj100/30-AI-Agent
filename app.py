import os
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Setup (optional if you already have static/template mount)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create uploads folder if not exists
UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)


@app.websocket("/ws/stream-audio")
async def stream_audio(websocket: WebSocket):
    await websocket.accept()
    # Generate a unique filename each time a client connects
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOADS_DIR, f"{file_id}.webm")

    try:
        with open(file_path, "wb") as audio_file:
            print(f"Receiving audio and saving to: {file_path}")
            while True:
                chunk = await websocket.receive_bytes()
                audio_file.write(chunk)
    except WebSocketDisconnect:
        print(f"WebSocket disconnected. Audio saved to {file_path}")
    except Exception as e:
        print(f"Error: {e}")
        await websocket.close()
