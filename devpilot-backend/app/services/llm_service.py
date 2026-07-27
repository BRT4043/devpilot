"""Single gateway for ALL LLM calls in DevPilot.

Every feature (commit messages, chat, explain, review, tests) calls
`complete()`. Provider switching, caching, and cost tracking live here
and nowhere else.
"""

import hashlib
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx
from redis.asyncio import Redis

from app.config import get_settings

settings = get_settings()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_STREAM_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent"
)
OPENAI_URL = "https://api.openai.com/v1/chat/completions"


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    cached: bool = False

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class StreamChunk:
    """One piece of a streamed completion. `done` chunks carry final token counts."""

    text: str = ""
    done: bool = False
    input_tokens: int = 0
    output_tokens: int = 0


def _cache_key(system: str | None, prompt: str, temperature: float) -> str:
    raw = json.dumps(
        [settings.llm_provider, settings.llm_model, system, prompt, temperature],
        ensure_ascii=False,
    )
    return "llm:" + hashlib.sha256(raw.encode()).hexdigest()


async def _call_gemini(system: str | None, prompt: str, temperature: float, max_tokens: int) -> LLMResult:
    body: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            GEMINI_URL.format(model=settings.llm_model),
            params={"key": settings.gemini_api_key},
            json=body,
        )
    resp.raise_for_status()
    data = resp.json()
    # Gemini can split a response across multiple parts (e.g. when a "thinking" model
    # runs out of budget mid-answer) — concatenate all of them, not just the first.
    text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
    usage = data.get("usageMetadata", {})
    return LLMResult(
        text=text,
        input_tokens=usage.get("promptTokenCount", 0),
        output_tokens=usage.get("candidatesTokenCount", 0),
    )


async def _call_openai(system: str | None, prompt: str, temperature: float, max_tokens: int) -> LLMResult:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            OPENAI_URL,
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.llm_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
    resp.raise_for_status()
    data = resp.json()
    usage = data.get("usage", {})
    return LLMResult(
        text=data["choices"][0]["message"]["content"],
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
    )


async def _stream_gemini(
    system: str | None, prompt: str, temperature: float, max_tokens: int
) -> AsyncIterator[StreamChunk]:
    body: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    input_tokens = output_tokens = 0
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream(
            "POST",
            GEMINI_STREAM_URL.format(model=settings.llm_model),
            params={"key": settings.gemini_api_key, "alt": "sse"},
            json=body,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                event = json.loads(line[len("data: ") :])
                for part in event.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                    text = part.get("text", "")
                    if text:
                        yield StreamChunk(text=text)
                usage = event.get("usageMetadata", {})
                input_tokens = usage.get("promptTokenCount", input_tokens)
                output_tokens = usage.get("candidatesTokenCount", output_tokens)

    yield StreamChunk(done=True, input_tokens=input_tokens, output_tokens=output_tokens)


async def _stream_openai(
    system: str | None, prompt: str, temperature: float, max_tokens: int
) -> AsyncIterator[StreamChunk]:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    input_tokens = output_tokens = 0
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream(
            "POST",
            OPENAI_URL,
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.llm_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
                "stream_options": {"include_usage": True},
            },
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                raw = line[len("data: ") :]
                if raw == "[DONE]":
                    break
                event = json.loads(raw)
                choices = event.get("choices") or []
                if choices:
                    text = choices[0].get("delta", {}).get("content") or ""
                    if text:
                        yield StreamChunk(text=text)
                usage = event.get("usage") or {}
                if usage:
                    input_tokens = usage.get("prompt_tokens", input_tokens)
                    output_tokens = usage.get("completion_tokens", output_tokens)

    yield StreamChunk(done=True, input_tokens=input_tokens, output_tokens=output_tokens)


_PROVIDERS = {"gemini": _call_gemini, "openai": _call_openai}
_STREAM_PROVIDERS = {"gemini": _stream_gemini, "openai": _stream_openai}


async def stream_complete(
    prompt: str,
    *,
    system: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> AsyncIterator[StreamChunk]:
    """Stream a completion chunk by chunk. Not cached — caching needs a complete response."""
    provider = _STREAM_PROVIDERS.get(settings.llm_provider)
    if provider is None:
        raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
    async for chunk in provider(system, prompt, temperature, max_tokens):
        yield chunk


async def complete(
    prompt: str,
    *,
    system: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1024,
    cache: Redis | None = None,
) -> LLMResult:
    """Run a completion. Pass a Redis connection to enable caching."""
    key = _cache_key(system, prompt, temperature)

    if cache is not None:
        hit = await cache.get(key)
        if hit:
            payload = json.loads(hit)
            return LLMResult(**payload, cached=True)

    provider = _PROVIDERS.get(settings.llm_provider)
    if provider is None:
        raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
    result = await provider(system, prompt, temperature, max_tokens)

    if cache is not None:
        await cache.set(
            key,
            json.dumps({
                "text": result.text,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            }),
            ex=settings.llm_cache_ttl_seconds,
        )
    return result
