from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_timeout_seconds: float
    web_results: int
    request_temperature: float
    agent_models: list[str]
    daily_api_limit: int
    storage_path: str
    history_window: int


def _read_int(name: str, default: int, min_value: int = 1) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= min_value else default


def _read_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _read_models(default_model: str) -> list[str]:
    raw = os.getenv("AGENT_MODELS", "").strip()
    if raw:
        models = [item.strip() for item in raw.split(",") if item.strip()]
    else:
        models = []

    if not models:
        models = [default_model]

    # Always keep exactly 4 workers for "4 models in parallel" mode.
    while len(models) < 4:
        models.append(models[-1])
    return models[:4]


def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing in .env")

    base_url = os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1").strip().rstrip("/")
    if not base_url:
        base_url = "http://127.0.0.1:11434/v1"

    default_model = os.getenv("LLM_MODEL", "openrouter/free").strip() or "openrouter/free"

    return Settings(
        telegram_bot_token=token,
        llm_base_url=base_url,
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        llm_model=default_model,
        llm_timeout_seconds=_read_float("LLM_TIMEOUT_SECONDS", 90.0),
        web_results=_read_int("WEB_RESULTS", 5),
        request_temperature=_read_float("REQUEST_TEMPERATURE", 0.25),
        agent_models=_read_models(default_model=default_model),
        daily_api_limit=_read_int("DAILY_API_LIMIT", 50),
        storage_path=os.getenv("STORAGE_PATH", "bot_data.sqlite3").strip() or "bot_data.sqlite3",
        history_window=_read_int("HISTORY_WINDOW", 4),
    )
