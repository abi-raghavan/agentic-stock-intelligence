from __future__ import annotations

import json
from typing import Any

import httpx

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def call_ollama(prompt: str, system: str | None = None) -> str:
    if not settings.enable_ollama:
        return "{}"

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": settings.ollama_model, "messages": messages, "stream": False, "format": "json"}
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "{}")
    except Exception as exc:
        logger.warning("ollama_call_failed", error=str(exc))
        return "{}"


def parse_json_response(content: str, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                pass
    return fallback
