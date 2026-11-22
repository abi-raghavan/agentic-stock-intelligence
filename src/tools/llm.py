import json
import re

import httpx

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


def llm_available() -> bool:
    return bool(settings.groq_api_key) or settings.enable_ollama


async def call_llm(
    prompt: str,
    system: str | None = None,
    *,
    json_mode: bool = True,
    max_tokens: int = 1024,
) -> str:
    """Free/fast LLM: Groq first, then local Ollama. Empty string if neither is configured."""
    if settings.groq_api_key:
        try:
            return await _call_groq(prompt, system=system, json_mode=json_mode, max_tokens=max_tokens)
        except Exception as exc:
            logger.warning("groq_call_failed", error=str(exc))
    if settings.enable_ollama:
        try:
            return await _call_ollama(prompt, system=system, json_mode=json_mode)
        except Exception as exc:
            logger.warning("ollama_call_failed", error=str(exc))
    return ""


async def call_ollama(prompt: str, system: str | None = None) -> str:
    """Backward-compatible wrapper used by older call sites."""
    return await call_llm(prompt, system=system, json_mode=True)


async def _call_groq(
    prompt: str,
    system: str | None = None,
    *,
    json_mode: bool = True,
    max_tokens: int = 1024,
) -> str:
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload: dict = {
        "model": settings.groq_model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"] or ""


async def _call_ollama(prompt: str, system: str | None = None, *, json_mode: bool = True) -> str:
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload: dict = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
    }
    if json_mode:
        payload["format"] = "json"

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")


def parse_json_response(content: str) -> dict:
    if not content:
        return {}
    text = content.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}
