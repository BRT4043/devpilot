"""Diagnose an error or stack trace: pull in the exact files it mentions plus
semantically related code, then ask the LLM for the likely root cause and a fix.
"""

import re

from redis.asyncio import Redis

from app.rag import retriever, vectorstore
from app.services import llm_service

MAX_FILES_FROM_TRACE = 4
MAX_CHUNKS_PER_FILE = 3
LINE_WINDOW = 60  # how far from the reported line a chunk still counts as "nearby"
SEMANTIC_K = 5
MAX_CONTEXT_CHARS = 10_000
MAX_TRACE_CHARS = 6_000

SYSTEM_PROMPT = (
    "You are DevPilot, helping a developer debug an error in their repository. "
    "You are given the error message or stack trace, code from the files it "
    "mentions, and other code from the repository that might be related. Explain "
    "in plain language what most likely went wrong and why, then suggest a "
    "concrete fix — reference exact files and lines where it helps. If the "
    "context genuinely isn't enough to pin down the cause, say what you can tell "
    "and what you'd need to see next instead of guessing confidently."
)

# File-looking paths ending in a common source extension, optionally followed by a
# line number — e.g. "app/services/x.py:42" or the quoted Python traceback form
# File "app/services/x.py", line 42
_FILE_LOCATION_RE = re.compile(
    r"(?P<path>[\w./\\-]+\.(?:py|js|jsx|ts|tsx|java|go|rb|php|c|cpp|h|hpp|cs|kt|swift))"
    r"(?:[:\"]?[,\s]*(?:line\s*)?(?P<line>\d+))?",
    re.IGNORECASE,
)


def _extract_file_locations(trace: str) -> list[tuple[str, int | None]]:
    """Unique (path, line) pairs mentioned in the trace, path-first order, line
    number kept if any mention of that path included one."""
    seen: dict[str, int | None] = {}
    for match in _FILE_LOCATION_RE.finditer(trace):
        path = match.group("path").replace("\\", "/").lstrip("./")
        line = int(match.group("line")) if match.group("line") else None
        if path not in seen:
            seen[path] = line
        elif seen[path] is None and line is not None:
            seen[path] = line
        if len(seen) >= MAX_FILES_FROM_TRACE:
            break
    return list(seen.items())


def _select_nearby_chunks(chunks: list[dict], line: int | None) -> list[dict]:
    """Don't dump a whole file — keep only chunks near the reported line (or the
    first few, if no line was given), capped to keep the prompt tight."""
    if not chunks:
        return []
    if line is not None:
        nearby = [
            c for c in chunks if c["start_line"] - LINE_WINDOW <= line <= c["end_line"] + LINE_WINDOW
        ]
        if nearby:
            chunks = nearby
    return chunks[:MAX_CHUNKS_PER_FILE]


def _format_context(chunks: list[dict], heading: str) -> str:
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
    return f"{heading}\n\n" + "\n\n".join(blocks)


def _extract_sources(chunks: list[dict]) -> list[dict]:
    return [
        {
            "file_path": c["file_path"],
            "start_line": c["start_line"],
            "end_line": c["end_line"],
            "language": c["language"],
            "score": c.get("score", 1.0),  # exact file matches aren't similarity-scored
        }
        for c in chunks
    ]


async def debug(
    repo_id: str,
    error_text: str,
    cache: Redis | None = None,
) -> tuple[llm_service.LLMResult, list[dict]]:
    error_text = error_text[:MAX_TRACE_CHARS]
    locations = _extract_file_locations(error_text)

    file_chunks: list[dict] = []
    if locations:
        client = vectorstore.get_client()
        try:
            for path, line in locations:
                all_chunks = await vectorstore.get_by_file(client, repo_id, path)
                file_chunks.extend(_select_nearby_chunks(all_chunks, line))
        finally:
            await client.close()

    semantic_chunks = await retriever.retrieve(repo_id, error_text, k=SEMANTIC_K)
    known_locations = {(c["file_path"], c["start_line"]) for c in file_chunks}
    semantic_chunks = [
        c for c in semantic_chunks if (c["file_path"], c["start_line"]) not in known_locations
    ]

    parts = [f"Error / stack trace:\n```\n{error_text}\n```"]
    file_block = _format_context(file_chunks, "Code from the files mentioned in the trace:")
    semantic_block = _format_context(semantic_chunks, "Other potentially related code:")
    if file_block:
        parts.append(file_block)
    if semantic_block:
        parts.append(semantic_block)

    prompt = "\n\n".join(parts)
    result = await llm_service.complete(prompt, system=SYSTEM_PROMPT, max_tokens=2000, cache=cache)

    return result, _extract_sources(file_chunks + semantic_chunks)
