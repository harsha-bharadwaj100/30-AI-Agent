from murf.client import Murf
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class MurfService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Murf API key not provided.")
        self.client = Murf(api_key=api_key)
        logger.info("Murf service initialized.")

    def generate_speech(self, text: str, voice_id: str = "en-US-terrell") -> str:
        try:
            logger.debug(
                f"Generating speech with Murf for text: {text[:50]}... using voice: {voice_id}"
            )
            api_response = self.client.text_to_speech.generate(
                text=text, voice_id=voice_id
            )
            if not api_response.audio_file:
                logger.error("Murf API response missing audio_file.")
                raise HTTPException(
                    status_code=500, detail="Audio URL not found in Murf API response."
                )

            logger.info(
                f"Successfully generated speech. Audio URL: {api_response.audio_file[:50]}..."
            )
            return api_response.audio_file
        except Exception as e:
            logger.exception("Error during Murf speech generation:")
            raise HTTPException(
                status_code=500,
                detail=f"Murf speech generation service error: {str(e)}",
            )
