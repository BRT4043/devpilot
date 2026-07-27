"""Walk a cloned repo and collect source files worth indexing."""

from dataclasses import dataclass
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", "out", ".next", "target",
    "venv", ".venv", "env", "__pycache__", ".pytest_cache", "vendor",
    "coverage", ".idea", ".vscode", "migrations",
}

# extension -> language tag used by the chunker
LANGUAGE_MAP = {
    ".py": "python", ".js": "js", ".jsx": "js", ".ts": "ts", ".tsx": "ts",
    ".java": "java", ".go": "go", ".rs": "rust", ".rb": "ruby",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp", ".cs": "csharp",
    ".php": "php", ".kt": "kotlin", ".swift": "swift", ".scala": "scala",
    ".dart": "dart", ".sql": "text", ".sh": "text", ".yaml": "text",
    ".yml": "text", ".toml": "text", ".md": "markdown", ".html": "html",
    ".css": "text",
}

MAX_FILE_BYTES = 500_000  # skip generated/minified monsters


@dataclass
class SourceFile:
    path: str          # relative to repo root, e.g. "app/services/auth.py"
    language: str
    content: str


def collect_files(repo_root: Path) -> list[SourceFile]:
    files: list[SourceFile] = []
    for p in sorted(repo_root.rglob("*")):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        lang = LANGUAGE_MAP.get(p.suffix.lower())
        if lang is None:
            continue
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
            content = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not content.strip():
            continue
        files.append(SourceFile(path=p.relative_to(repo_root).as_posix(), language=lang, content=content))
    return files
