"""Turn a connected repo into technical interview questions grounded in its
actual architecture and technology choices — not generic trivia.
"""

from redis.asyncio import Redis

from app.rag import retriever
from app.services import llm_service

TOP_K = 15
MAX_CONTEXT_CHARS = 14_000
BROAD_QUERY = (
    "project architecture, technology stack, database, authentication, API design, "
    "background jobs, configuration, deployment, main entry points"
)

SYSTEM_PROMPT = (
    "You are DevPilot, generating technical interview questions from a real "
    "codebase — the kind a hiring manager or tech lead would actually ask about "
    "THIS project, not generic trivia. You are given a broad sample of the "
    "repository's code and structure. Write 8-10 questions covering a mix of: "
    "architecture and design decisions, specific technology choices and their "
    "trade-offs, how key flows work end to end, and scaling or failure "
    "considerations. For each question, add one short line in italics hinting "
    "at what a strong answer would touch on (not the full answer), grounded in "
    "what you actually saw in the code — don't invent details the context "
    "doesn't support. Number the questions. Keep it scannable, not a wall of text."
)


def _format_context(chunks: list[dict]) -> str:
    if not chunks:
        return "(No code was retrieved from the repository.)"
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


async def generate(repo_id: str, cache: Redis | None = None) -> llm_service.LLMResult:
    chunks = await retriever.retrieve(repo_id, BROAD_QUERY, k=TOP_K)
    prompt = (
        f"Repository context:\n{_format_context(chunks)}\n\nGenerate the interview questions now."
    )
    return await llm_service.complete(
        prompt, system=SYSTEM_PROMPT, temperature=0.4, max_tokens=3000, cache=cache
    )
