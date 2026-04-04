import logging
import os

import assemblyai as aai
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from murf.client import Murf

from services.ingestion_service import ingest_upload
from services.persistence_service import PersistenceService
from services.vector_service import VectorService

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
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))

# Validate API Keys at startup
if not MURF_API_KEY:
    logger.warning("Missing API key: MURF_API_KEY")
if not ASSEMBLYAI_API_KEY:
    logger.warning("Missing API key: ASSEMBLYAI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("Missing API key: GEMINI_API_KEY")

# Configure APIs
if ASSEMBLYAI_API_KEY:
    aai.settings.api_key = ASSEMBLYAI_API_KEY
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
if MURF_API_KEY:
    murf = Murf(api_key=MURF_API_KEY)

# --- Persistence and Retrieval Services ---
persistence_service = PersistenceService(os.getenv("SQLITE_DB_PATH", "data/app.db"))

try:
    vector_service = VectorService(
        persist_dir=os.getenv("CHROMA_DIR", "data/chroma"),
        collection_name=os.getenv("CHROMA_COLLECTION", "rag_chunks"),
        embedding_model=os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ),
    )
except Exception as vector_error:
    logger.error(f"Vector service failed to initialize: {vector_error}")
    vector_service = None

AGENT_PERSONA = (
    "You are 'Nova', a witty, slightly sassy robot assistant. "
    "Prioritize retrieved context when available and cite sources clearly. "
    "If retrieval does not contain the answer, you may answer from general knowledge "
    "and explicitly mention that you are using general knowledge. "
    "Keep answers concise and actionable."
)

# --- Error Response Templates ---
ERROR_RESPONSES = {
    "stt_error": "I'm having trouble hearing you right now. Could you please try again?",
    "llm_error": "I'm having trouble thinking right now. Please give me a moment and try again.",
    "api_key_error": "My services aren't configured correctly. Please contact support.",
    "general_error": "Something unexpected happened. Please try again in a moment.",
}


# --- Utility Function for Fallback Audio ---
def create_fallback_audio_response(error_message: str):
    """Attempts to create a fallback audio response using TTS."""
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


def _render_recent_history(history_items: list[dict], limit: int = 8) -> str:
    if not history_items:
        return "No prior conversation."

    lines = []
    for item in history_items[-limit:]:
        role = item.get("role", "user")
        parts = item.get("parts", [""])
        content = parts[0] if parts else ""
        lines.append(f"{role.upper()}: {content}")
    return "\n".join(lines)


def _build_rag_prompt(
    user_message: str,
    history_items: list[dict],
    retrieved_chunks: list[dict],
) -> str:
    history_text = _render_recent_history(history_items)

    if retrieved_chunks:
        context_blocks = []
        for idx, chunk in enumerate(retrieved_chunks, start=1):
            meta = chunk.get("metadata") or {}
            source = meta.get("source", "unknown")
            chunk_idx = meta.get("chunk_index", "?")
            context_blocks.append(
                f"[{idx}] source={source} chunk={chunk_idx}\n{chunk.get('content', '')}"
            )
        context_text = "\n\n".join(context_blocks)
    else:
        context_text = "No retrieved context available."

    return (
        "Use this structure:\n"
        "1) Answer with retrieved context when relevant.\n"
        "2) If context is insufficient, answer using general knowledge and state that clearly.\n"
        "3) End with a short helpful follow-up.\n\n"
        f"Recent conversation:\n{history_text}\n\n"
        f"Retrieved context:\n{context_text}\n\n"
        f"User question:\n{user_message}"
    )


def _extract_sources(retrieved_chunks: list[dict]) -> list[dict]:
    seen = set()
    sources = []
    for chunk in retrieved_chunks:
        metadata = chunk.get("metadata") or {}
        source_key = (
            metadata.get("doc_id"),
            metadata.get("source"),
            metadata.get("chunk_index"),
        )
        if source_key in seen:
            continue
        seen.add(source_key)
        sources.append(
            {
                "doc_id": metadata.get("doc_id"),
                "source": metadata.get("source", "unknown"),
                "chunk_index": metadata.get("chunk_index"),
                "distance": chunk.get("distance"),
            }
        )
    return sources


# --- Frontend Route ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main index.html page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/chat/{session_id}")
async def get_chat_history(session_id: str):
    history = persistence_service.get_session_messages(session_id=session_id, limit=50)
    return {"session_id": session_id, "messages": history}


@app.get("/documents")
async def list_documents():
    return {"documents": persistence_service.list_documents()}


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if vector_service is None:
        raise HTTPException(
            status_code=503,
            detail="Vector service is not available. Check embedding dependencies.",
        )
    result = await ingest_upload(file, persistence_service, vector_service)
    return result


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    if vector_service is not None:
        vector_service.delete_by_doc_id(doc_id)
    deleted = persistence_service.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"deleted": True, "doc_id": doc_id}


# --- Robust Conversational Agent Endpoint ---
@app.post("/agent/chat/{session_id}")
async def agent_chat(session_id: str, audio: UploadFile = File(...)):
    """
    Handles a full conversational turn with error handling:
    Audio (user) -> STT -> History -> LLM -> History -> TTS -> Audio (bot)
    """
    logger.info(f"Processing chat request for session: {session_id}")
    # Check for API key availability
    if not ASSEMBLYAI_API_KEY or not GEMINI_API_KEY or not MURF_API_KEY:
        logger.error("One or more API keys are not configured.")
        return create_fallback_audio_response(ERROR_RESPONSES["api_key_error"])

    try:
        # 1. TRANSCRIPTION PHASE
        logger.info("Starting transcription...")
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio.file)

        if transcript.status == aai.TranscriptStatus.error:
            logger.error(f"STT Error: {transcript.error}")
            return create_fallback_audio_response(ERROR_RESPONSES["stt_error"])

        if not transcript.text or transcript.text.strip() == "":
            logger.warning("STT returned empty transcript.")
            return create_fallback_audio_response(
                "I didn't catch that. Could you please speak clearly?"
            )

        user_message = transcript.text.strip()
        logger.info(f"Transcription successful: {user_message[:50]}...")

        # 2. CHAT HISTORY MANAGEMENT + USER MESSAGE PERSISTENCE
        prior_history = persistence_service.get_session_messages(session_id=session_id)
        persistence_service.save_message(session_id, "user", user_message)

        # 3. RETRIEVAL PHASE
        retrieved_chunks = []
        if vector_service is not None:
            try:
                retrieved_chunks = vector_service.query(user_message, top_k=RAG_TOP_K)
            except Exception as retrieval_error:
                logger.error(f"Retrieval failed: {retrieval_error}")
                retrieved_chunks = []

        rag_prompt = _build_rag_prompt(user_message, prior_history, retrieved_chunks)

        # 4. LLM RESPONSE GENERATION
        logger.info("Generating LLM response...")
        model = genai.GenerativeModel(
            "gemini-2.5-flash-lite", system_instruction=AGENT_PERSONA
        )

        llm_response = model.generate_content(rag_prompt)
        llm_text = (llm_response.text or "").strip()
        if not llm_text:
            llm_text = ERROR_RESPONSES["llm_error"]
        logger.info(f"LLM response generated: {llm_text[:50]}...")

        sources = _extract_sources(retrieved_chunks)
        persistence_service.save_message(
            session_id,
            "model",
            llm_text,
            metadata={"sources": sources, "retrieval_count": len(retrieved_chunks)},
        )

        # 5. TEXT-TO-SPEECH GENERATION
        logger.info("Generating TTS response...")

        # Handle Murf's 3000 character limit
        if len(llm_text) > 3000:
            llm_text = (
                llm_text[:2950] + "... I have more to say, but I'll keep it brief."
            )
            logger.warning("LLM response truncated for TTS.")

        murf_response = murf.text_to_speech.generate(
            text=llm_text, voice_id="en-US-natalie"  # You can change this voice
        )

        logger.info("TTS generation successful.")
        return {
            "audio_url": murf_response.audio_file,
            "text": llm_text,
            "sources": sources,
            "retrieval_count": len(retrieved_chunks),
            "error": False,
        }

    except Exception as e:
        logger.error(f"Unexpected error in agent_chat: {str(e)}")
        return create_fallback_audio_response(ERROR_RESPONSES["general_error"])
    finally:
        try:
            if audio and hasattr(audio, "file") and not audio.file.closed:
                audio.file.close()
        except Exception as e:
            logger.error(f"Error closing audio file: {str(e)}")
