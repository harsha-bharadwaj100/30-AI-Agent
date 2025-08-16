# services/gemini_service.py
import google.generativeai as genai
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Google Gemini API key not provided.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-pro")  # Using gemini-pro for text
        logger.info("Google Gemini service initialized.")

    def get_chat_response(self, prompt: str, history: list = None) -> str:
        """
        Placeholder for interacting with the Gemini LLM.
        In a real scenario, you'd manage conversation history and model parameters here.
        """
        try:
            logger.debug(f"Getting Gemini response for prompt: {prompt[:50]}...")
            # This is a simplified example. For actual conversation,
            # you'd use a chat session and pass history.
            response = self.model.generate_content(prompt)
            # Check if response has parts and text
            if response.parts and response.parts[0].text:
                return response.parts[0].text
            else:
                logger.warning(
                    f"Gemini returned no text for prompt: {prompt}. Full response: {response}"
                )
                return "I'm sorry, I couldn't generate a response."
        except Exception as e:
            logger.exception("Error during Gemini API call:")
            raise HTTPException(
                status_code=500, detail=f"Gemini service error: {str(e)}"
            )
