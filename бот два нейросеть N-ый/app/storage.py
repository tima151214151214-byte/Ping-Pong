from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _utc_day() -> str:
    return datetime.now(timezone.utc).date().isoformat()


class BotStorage:
    def __init__(self, db_path: str) -> None:
        self._path = Path(db_path)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        chat_id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        registered_at TEXT NOT NULL,
                        denomination TEXT NOT NULL DEFAULT 'orthodox',
                        answer_length TEXT NOT NULL DEFAULT 'long',
                        explain_style TEXT NOT NULL DEFAULT 'orthodox',
                        reasoning_mode TEXT NOT NULL DEFAULT 'balanced',
                        model_preset TEXT NOT NULL DEFAULT 'router_free'
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS usage (
                        day TEXT PRIMARY KEY,
                        api_calls INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ai_config (
                        chat_id INTEGER PRIMARY KEY,
                        base_url TEXT NOT NULL,
                        api_key TEXT NOT NULL,
                        model TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS short_memory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER NOT NULL,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                self._ensure_user_columns(conn)
                conn.commit()

    def _ensure_user_columns(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(users)").fetchall()
        existing = {str(row["name"]) for row in rows}

        if "denomination" not in existing:
            conn.execute(
                "ALTER TABLE users ADD COLUMN denomination TEXT NOT NULL DEFAULT 'orthodox'"
            )
        if "answer_length" not in existing:
            conn.execute(
                "ALTER TABLE users ADD COLUMN answer_length TEXT NOT NULL DEFAULT 'long'"
            )
        if "explain_style" not in existing:
            conn.execute(
                "ALTER TABLE users ADD COLUMN explain_style TEXT NOT NULL DEFAULT 'orthodox'"
            )
        if "reasoning_mode" not in existing:
            conn.execute(
                "ALTER TABLE users ADD COLUMN reasoning_mode TEXT NOT NULL DEFAULT 'balanced'"
            )
        if "model_preset" not in existing:
            conn.execute(
                "ALTER TABLE users ADD COLUMN model_preset TEXT NOT NULL DEFAULT 'router_free'"
            )

    def get_user(self, chat_id: int) -> dict[str, Any] | None:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT chat_id, name, registered_at, denomination, answer_length "
                    ", explain_style, reasoning_mode, model_preset "
                    "FROM users WHERE chat_id = ?",
                    (chat_id,),
                ).fetchone()
        if row is None:
            return None
        return {
            "chat_id": int(row["chat_id"]),
            "name": str(row["name"]),
            "registered_at": str(row["registered_at"]),
            "denomination": str(row["denomination"] or "orthodox"),
            "answer_length": str(row["answer_length"] or "long"),
            "explain_style": str(row["explain_style"] or "orthodox"),
            "reasoning_mode": str(row["reasoning_mode"] or "balanced"),
            "model_preset": str(row["model_preset"] or "router_free"),
        }

    def get_ai_config(self, chat_id: int) -> dict[str, str] | None:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT chat_id, base_url, api_key, model, updated_at "
                    "FROM ai_config WHERE chat_id = ?",
                    (chat_id,),
                ).fetchone()
        if row is None:
            return None
        return {
            "chat_id": str(row["chat_id"]),
            "base_url": str(row["base_url"]),
            "api_key": str(row["api_key"]),
            "model": str(row["model"]),
            "updated_at": str(row["updated_at"]),
        }

    def upsert_ai_config(self, chat_id: int, base_url: str, api_key: str, model: str) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO ai_config (chat_id, base_url, api_key, model, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(chat_id) DO UPDATE SET
                        base_url = excluded.base_url,
                        api_key = excluded.api_key,
                        model = excluded.model,
                        updated_at = excluded.updated_at
                    """,
                    (chat_id, base_url.strip(), api_key.strip(), model.strip(), _utc_now_iso()),
                )
                conn.commit()

    def append_short_memory(self, chat_id: int, question: str, answer: str, window: int = 4) -> None:
        keep = max(1, min(window, 12))
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO short_memory (chat_id, question, answer, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (chat_id, question.strip(), answer.strip(), _utc_now_iso()),
                )
                conn.execute(
                    """
                    DELETE FROM short_memory
                    WHERE chat_id = ?
                      AND id NOT IN (
                          SELECT id FROM short_memory
                          WHERE chat_id = ?
                          ORDER BY id DESC
                          LIMIT ?
                      )
                    """,
                    (chat_id, chat_id, keep),
                )
                conn.commit()

    def get_short_memory(self, chat_id: int, window: int = 4) -> list[tuple[str, str]]:
        keep = max(1, min(window, 12))
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT question, answer FROM short_memory
                    WHERE chat_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (chat_id, keep),
                ).fetchall()
        ordered = list(reversed(rows))
        return [(str(row["question"]), str(row["answer"])) for row in ordered]

    def upsert_user(self, chat_id: int, name: str) -> None:
        name = name.strip()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO users (
                        chat_id, name, registered_at, denomination, answer_length,
                        explain_style, reasoning_mode, model_preset
                    )
                    VALUES (?, ?, ?, 'orthodox', 'long', 'orthodox', 'balanced', 'router_free')
                    ON CONFLICT(chat_id) DO UPDATE SET
                        name = excluded.name
                    """,
                    (chat_id, name, _utc_now_iso()),
                )
                conn.commit()

    def update_denomination(self, chat_id: int, denomination: str) -> None:
        value = "catholic" if denomination == "catholic" else "orthodox"
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE users SET denomination = ? WHERE chat_id = ?",
                    (value, chat_id),
                )
                conn.commit()

    def update_answer_length(self, chat_id: int, answer_length: str) -> None:
        allowed = {"very_short", "short", "medium", "long", "very_long"}
        value = answer_length if answer_length in allowed else "long"
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE users SET answer_length = ? WHERE chat_id = ?",
                    (value, chat_id),
                )
                conn.commit()

    def update_explain_style(self, chat_id: int, explain_style: str) -> None:
        allowed = {"orthodox", "simple", "layered"}
        value = explain_style if explain_style in allowed else "orthodox"
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE users SET explain_style = ? WHERE chat_id = ?",
                    (value, chat_id),
                )
                conn.commit()

    def update_reasoning_mode(self, chat_id: int, reasoning_mode: str) -> None:
        allowed = {"fast", "balanced", "deep"}
        value = reasoning_mode if reasoning_mode in allowed else "balanced"
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE users SET reasoning_mode = ? WHERE chat_id = ?",
                    (value, chat_id),
                )
                conn.commit()

    def update_model_preset(self, chat_id: int, model_preset: str) -> None:
        allowed = {"router_free", "qwen_4b", "gpt_oss_20b", "mistral_24b"}
        value = model_preset if model_preset in allowed else "router_free"
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE users SET model_preset = ? WHERE chat_id = ?",
                    (value, chat_id),
                )
                conn.commit()

    def increment_api_calls(self, amount: int = 1) -> int:
        if amount < 1:
            return self.get_api_calls_today()

        day = _utc_day()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO usage (day, api_calls) VALUES (?, 0) "
                    "ON CONFLICT(day) DO NOTHING",
                    (day,),
                )
                conn.execute(
                    "UPDATE usage SET api_calls = api_calls + ? WHERE day = ?",
                    (amount, day),
                )
                row = conn.execute(
                    "SELECT api_calls FROM usage WHERE day = ?",
                    (day,),
                ).fetchone()
                conn.commit()

        return int(row["api_calls"]) if row else 0

    def get_api_calls_today(self) -> int:
        day = _utc_day()
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT api_calls FROM usage WHERE day = ?",
                    (day,),
                ).fetchone()
        if row is None:
            return 0
        return int(row["api_calls"])
