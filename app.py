import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Initialize the FastAPI application
app = FastAPI()


# Pydantic model to define the structure of the request body
class TTSRequest(BaseModel):
    text: str
    voice_id: str = "en-US-natalie"  # A default voice ID


# Murf API configuration
MURF_API_URL = "https://api.murf.ai/v1/speech/generate"
MURF_API_KEY = os.getenv("MURF_API_KEY")


@app.post("/generate-audio/")
async def generate_audio(request: TTSRequest):
    """
    Accepts text and a voice ID, calls the Murf TTS API,
    and returns the URL of the generated audio file.
    """
    if not MURF_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="API key not found. Ensure it is set in your .env file.",
        )

    headers = {"Content-Type": "application/json", "api-key": MURF_API_KEY}

    payload = {"text": request.text, "voiceId": request.voice_id, "format": "MP3"}

    try:
        # Make the POST request to the Murf API
        response = requests.post(MURF_API_URL, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        # --- THIS IS THE FIX ---
        # The key from Murf's API is 'audioFile', not 'audioUrl'
        audio_url = data.get("audioFile")

        if not audio_url:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Audio URL not found in Murf API response.",
                    "murf_api_response": data,
                },
            )

        return {"audio_url": audio_url}

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error calling Murf API: {e}")
