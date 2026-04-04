from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile

from services.persistence_service import PersistenceService
from services.vector_service import VectorService

ALLOWED_EXTENSIONS = {".txt", ".md"}


def _chunk_text(text: str, chunk_size: int = 180, overlap: int = 40) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    step = max(1, chunk_size - overlap)
    for start in range(0, len(words), step):
        section = words[start : start + chunk_size]
        if not section:
            continue
        chunks.append(" ".join(section))

    return chunks


async def ingest_upload(
    upload: UploadFile,
    persistence_service: PersistenceService,
    vector_service: VectorService,
) -> dict[str, Any]:
    filename = upload.filename or "untitled.txt"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Only .txt and .md are supported in MVP.",
        )

    raw = await upload.read()
    text = raw.decode("utf-8", errors="ignore").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    doc_id = persistence_service.create_document(filename, upload.content_type)
    chunks = _chunk_text(text)
    if not chunks:
        raise HTTPException(
            status_code=400, detail="No usable text chunks were created."
        )

    metadata_list = [
        {"doc_id": doc_id, "source": filename, "chunk_index": idx}
        for idx, _ in enumerate(chunks)
    ]
    vector_ids = [f"{doc_id}:{idx}" for idx, _ in enumerate(chunks)]

    persistence_service.save_document_chunks(doc_id, chunks, metadata_list)
    vector_service.upsert_chunks(vector_ids, chunks, metadata_list)

    return {
        "doc_id": doc_id,
        "filename": filename,
        "chunks_created": len(chunks),
    }
