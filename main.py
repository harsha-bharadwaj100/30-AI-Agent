import uvicorn
from app import app  # Import the FastAPI app instance from app.py
import logging

# Configure basic logging for the entry point
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting Uvicorn server for AI Voice Agent.")
    uvicorn.run(
        "app:app",  # Point to the app instance in app.py
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
