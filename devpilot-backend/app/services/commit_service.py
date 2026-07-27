"""Generate commit messages from a git diff."""

from redis.asyncio import Redis

from app.services import llm_service

MAX_DIFF_CHARS = 12_000  # keep prompts cheap; huge diffs get truncated

SYSTEM_PROMPT = (
    "You are an expert software engineer writing git commit messages. "
    "Reply with ONLY the commit message — no explanations, no markdown fences, no quotes."
)

STYLE_INSTRUCTIONS = {
    "conventional": (
        "Use Conventional Commits format: type(scope): summary. "
        "Types: feat, fix, docs, style, refactor, test, chore. "
        "Summary line under 72 characters, imperative mood. "
        "If the change is complex, add a short body after a blank line."
    ),
    "simple": "Write a single imperative sentence under 72 characters.",
}


def _truncate_diff(diff: str) -> str:
    if len(diff) <= MAX_DIFF_CHARS:
        return diff
    return diff[:MAX_DIFF_CHARS] + "\n... [diff truncated] ..."


async def generate(diff: str, style: str, cache: Redis | None = None) -> llm_service.LLMResult:
    instructions = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["conventional"])
    prompt = (
        f"{instructions}\n\n"
        f"Write a commit message for this diff:\n\n"
        f"```diff\n{_truncate_diff(diff)}\n```"
    )
    result = await llm_service.complete(prompt, system=SYSTEM_PROMPT, cache=cache)
    # Models sometimes wrap output in fences despite instructions — strip them.
    result.text = result.text.strip().strip("`").strip()
    return result
