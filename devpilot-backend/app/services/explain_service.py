"""Explain a code snippet, grounded in related context retrieved from the repo.

Unlike chat, this is stateless — nothing is persisted. The frontend supplies
the snippet (from the editor/viewer); we use it as a retrieval query to pull
in related excerpts from the rest of the codebase before asking the LLM.
"""

from redis.asyncio import Redis

from app.rag import retriever
from app.services import llm_service

TOP_K = 5
MAX_CONTEXT_CHARS = 8_000
MAX_CODE_CHARS = 8_000

SYSTEM_PROMPT = (
    "You are DevPilot, an assistant that explains code in plain, friendly "
    "language — clear enough for a beginner, still useful for an expert. You are "
    "given a code snippet to explain and, where available, related excerpts "
    "retrieved from the same repository for extra context. Explain what the code "
    "does in everyday terms first, then, only if it genuinely adds value, how it "
    "fits into the surrounding system. Call out anything truly notable (edge "
    "cases, side effects, risks) — skip it if there's nothing worth flagging. "
    "Keep it short; avoid jargon unless you briefly explain it."
)


def _format_context(chunks: list[dict]) -> str:
    if not chunks:
        return ""
    blocks = []
    total = 0
    for c in chunks:
        header = f"### {c['file_path']}:{c['start_line']}-{c['end_line']} ({c['language']})"
        block = f"{header}\n```{c['language']}\n{c['text']}\n```"
        if blocks and total + len(block) > MAX_CONTEXT_CHARS:
            break
        blocks.append(block)
        total += len(block)
    return "\n\n".join(blocks)


def _truncate(code: str) -> str:
    if len(code) <= MAX_CODE_CHARS:
        return code
    return code[:MAX_CODE_CHARS] + "\n... [truncated] ..."


def _extract_sources(chunks: list[dict]) -> list[dict]:
    return [
        {
            "file_path": c["file_path"],
            "start_line": c["start_line"],
            "end_line": c["end_line"],
            "language": c["language"],
            "score": c["score"],
        }
        for c in chunks
    ]


async def explain(
    repo_id: str,
    code: str,
    file_path: str | None = None,
    language: str | None = None,
    cache: Redis | None = None,
) -> tuple[llm_service.LLMResult, list[dict]]:
    chunks = await retriever.retrieve(repo_id, code, k=TOP_K)
    context = _format_context(chunks)

    location = f" from `{file_path}`" if file_path else ""
    parts = [
        f"Explain this code{location}:",
        f"```{language or ''}\n{_truncate(code)}\n```",
    ]
    if context:
        parts.append(f"Related context from the repository:\n\n{context}")

    prompt = "\n\n".join(parts)
    result = await llm_service.complete(prompt, system=SYSTEM_PROMPT, cache=cache)
    return result, _extract_sources(chunks)
