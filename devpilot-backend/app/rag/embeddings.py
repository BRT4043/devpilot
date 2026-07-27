"""Turn text into vectors, batched. Provider follows LLM_PROVIDER."""

import httpx

from app.config import get_settings

settings = get_settings()

GEMINI_BATCH_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"
)
OPENAI_EMBED_URL = "https://api.openai.com/v1/embeddings"

BATCH_SIZE = 64


async def _embed_gemini(texts: list[str]) -> list[list[float]]:
    body = {
        "requests": [
            {
                "model": f"models/{settings.embedding_model}",
                "content": {"parts": [{"text": t}]},
            }
            for t in texts
        ]
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            GEMINI_BATCH_URL.format(model=settings.embedding_model),
            params={"key": settings.gemini_api_key},
            json=body,
        )
    resp.raise_for_status()
    return [e["values"] for e in resp.json()["embeddings"]]


async def _embed_openai(texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            OPENAI_EMBED_URL,
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"model": settings.embedding_model, "input": texts},
        )
    resp.raise_for_status()
    data = sorted(resp.json()["data"], key=lambda d: d["index"])
    return [d["embedding"] for d in data]


async def embed_batch(texts: list[str]) -> list[list[float]]:
    fn = _embed_gemini if settings.llm_provider == "gemini" else _embed_openai
    vectors: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        vectors.extend(await fn(texts[i : i + BATCH_SIZE]))
    return vectors


async def embed_query(text: str) -> list[float]:
    return (await embed_batch([text]))[0]
