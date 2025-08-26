import os
import asyncio
import assemblyai as aai
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv

load_dotenv()
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
aai.settings.api_key = ASSEMBLYAI_API_KEY

app = FastAPI()


@app.websocket("/ws/stream-for-transcription")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection accepted.")

    # Initialize the AssemblyAI real-time transcriber
    transcriber = aai.RealtimeTranscriber(
        sample_rate=16000,  # 16kHz, as required!
        encoding="pcm_s16le",  # PCM 16-bit little-endian
        channels=1,
    )

    # Start AssemblyAI websocket connection
    async with transcriber:
        print("Connected to AssemblyAI websocket for transcription...")

        # Start async task to fetch transcripts as they arrive
        async def receive_transcripts():
            async for transcript in transcriber:
                if transcript.text:
                    print("Transcript:", transcript.text)

        transcript_task = asyncio.create_task(receive_transcripts())

        try:
            while True:
                # Receive audio chunk (as bytes) from the client
                chunk = await websocket.receive_bytes()
                # Forward to AssemblyAI transcriber
                await transcriber.send(chunk)
        except WebSocketDisconnect:
            print("WebSocket client disconnected.")
        finally:
            await transcriber.close()
            transcript_task.cancel()
