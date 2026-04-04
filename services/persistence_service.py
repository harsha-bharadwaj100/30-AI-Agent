import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any


class PersistenceService:
    def __init__(self, db_path: str = "data/app.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
                """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    content_type TEXT,
                    created_at TEXT NOT NULL
                )
                """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(doc_id) REFERENCES documents(doc_id)
                )
                """)
            conn.commit()

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _upsert_session(self, session_id: str) -> None:
        now = self._utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, created_at, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET updated_at=excluded.updated_at
                """,
                (session_id, now, now),
            )
            conn.commit()

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._upsert_session(session_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (session_id, role, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    role,
                    content,
                    json.dumps(metadata or {}),
                    self._utc_now(),
                ),
            )
            conn.commit()

    def get_session_messages(
        self, session_id: str, limit: int = 12
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()

        ordered_rows = list(reversed(rows))
        return [
            {
                "role": row["role"],
                "parts": [row["content"]],
                "created_at": row["created_at"],
            }
            for row in ordered_rows
        ]

    def create_document(self, filename: str, content_type: str | None) -> str:
        doc_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents (doc_id, filename, content_type, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (doc_id, filename, content_type, self._utc_now()),
            )
            conn.commit()
        return doc_id

    def save_document_chunks(
        self,
        doc_id: str,
        chunks: list[str],
        metadata_list: list[dict[str, Any]],
    ) -> None:
        created_at = self._utc_now()
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO chunks (doc_id, chunk_index, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        doc_id,
                        idx,
                        chunk,
                        json.dumps(metadata_list[idx]),
                        created_at,
                    )
                    for idx, chunk in enumerate(chunks)
                ],
            )
            conn.commit()

    def list_documents(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT d.doc_id, d.filename, d.content_type, d.created_at, COUNT(c.id) AS chunk_count
                FROM documents d
                LEFT JOIN chunks c ON c.doc_id = d.doc_id
                GROUP BY d.doc_id
                ORDER BY d.created_at DESC
                """).fetchall()

        return [dict(row) for row in rows]

    def delete_document(self, doc_id: str) -> bool:
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
            result = conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            conn.commit()
            return result.rowcount > 0
