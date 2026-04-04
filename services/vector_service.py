import os
from typing import Any

import chromadb


class _SentenceTransformerEmbeddingFunction:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def __call__(self, input: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(input, normalize_embeddings=True)
        return embeddings.tolist()


class VectorService:
    def __init__(
        self,
        persist_dir: str = "data/chroma",
        collection_name: str = "rag_chunks",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        os.makedirs(persist_dir, exist_ok=True)
        client = chromadb.PersistentClient(path=persist_dir)

        embedding_function = _SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )
        self.collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(
        self,
        ids: list[str],
        chunks: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        self.collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)

    def query(self, query_text: str, top_k: int = 4) -> list[dict[str, Any]]:
        result = self.collection.query(query_texts=[query_text], n_results=top_k)

        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        rows: list[dict[str, Any]] = []
        for idx, chunk_id in enumerate(ids):
            rows.append(
                {
                    "id": chunk_id,
                    "content": docs[idx] if idx < len(docs) else "",
                    "metadata": metas[idx] if idx < len(metas) else {},
                    "distance": distances[idx] if idx < len(distances) else None,
                }
            )
        return rows

    def delete_by_doc_id(self, doc_id: str) -> None:
        self.collection.delete(where={"doc_id": doc_id})
