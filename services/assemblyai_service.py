import assemblyai as aai
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class AssemblyAIService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("AssemblyAI API key not provided.")
        aai.settings.api_key = api_key
        self.transcriber = aai.Transcriber()
        logger.info("AssemblyAI service initialized.")

    def transcribe_audio(self, audio_file) -> str:
        try:
            logger.debug("Starting transcription with AssemblyAI...")
            transcript = self.transcriber.transcribe(audio_file)

            if transcript.status == aai.TranscriptStatus.error:
                logger.error(f"AssemblyAI transcription error: {transcript.error}")
                raise HTTPException(
                    status_code=500, detail=f"Transcription failed: {transcript.error}"
                )

            if not transcript.text:
                logger.warning("AssemblyAI returned empty transcript.")
                # It's better to return an empty string rather than raise 400 here,
                # as the higher-level logic might handle empty transcripts differently.
                return ""

            logger.info(
                f"Successfully transcribed audio. Text: {transcript.text[:50]}..."
            )
            return transcript.text
        except Exception as e:
            logger.exception("Error during AssemblyAI transcription:")
            raise HTTPException(
                status_code=500,
                detail=f"AssemblyAI transcription service error: {str(e)}",
            )
