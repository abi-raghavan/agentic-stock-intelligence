import json

import httpx

from src.config import get_settings

settings = get_settings()


async def call_ollama(prompt: str, system: str | None = None) -> str:
    if not settings.enable_ollama:
        return ""

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": settings.ollama_model, "messages": messages, "stream": False, "format": "json"}
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")


def parse_json_response(content: str) -> dict:
    if not content:
        return {}
    return json.loads(content)
