from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx


class LLMClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        on_request_complete: Callable[[], None] | None = None,
    ) -> None:
        self._url = self._build_url(base_url)
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._on_request_complete = on_request_complete

    @property
    def default_model(self) -> str:
        return self._model

    @staticmethod
    def _build_url(base_url: str) -> str:
        url = base_url.strip().rstrip("/")
        if url.endswith("/chat/completions"):
            return url
        if url.endswith("/v1"):
            return f"{url}/chat/completions"
        return f"{url}/v1/chat/completions"

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int = 900,
        model: str | None = None,
    ) -> str:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload: dict[str, Any] = {
            "model": (model or self._model).strip() or self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self._url, json=payload, headers=headers)
            response.raise_for_status()
            if self._on_request_complete:
                self._on_request_complete()
            data = response.json()

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("LLM returned no choices")

        message = choices[0].get("message", {})
        content = self._extract_content(message=message, choice=choices[0])
        if not content:
            raise RuntimeError("LLM returned empty response")
        return content

    @staticmethod
    def _extract_content(message: object, choice: object) -> str:
        if isinstance(message, dict):
            content = LLMClient._normalize_content(message.get("content"))
            if content:
                return content

        if isinstance(choice, dict):
            text = str(choice.get("text", "")).strip()
            if text:
                return text
        return ""

    @staticmethod
    def _normalize_content(raw_content: object) -> str:
        if raw_content is None:
            return ""

        if isinstance(raw_content, str):
            return raw_content.strip()

        if isinstance(raw_content, dict):
            for key in ("text", "content"):
                value = raw_content.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            return ""

        if isinstance(raw_content, list):
            parts: list[str] = []
            for chunk in raw_content:
                if isinstance(chunk, str):
                    chunk_text = chunk.strip()
                    if chunk_text:
                        parts.append(chunk_text)
                    continue

                if not isinstance(chunk, dict):
                    continue

                for key in ("text", "content"):
                    value = chunk.get(key)
                    if isinstance(value, str) and value.strip():
                        parts.append(value.strip())
                        break
            return "\n".join(parts).strip()

        return ""
