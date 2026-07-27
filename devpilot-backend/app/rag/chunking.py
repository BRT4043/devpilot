"""Split source files into chunks on function/class boundaries where possible."""

from dataclasses import dataclass, field

from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from app.rag.ingestion import SourceFile

CHUNK_SIZE = 1500      # ~characters; roughly 350-400 tokens of code
CHUNK_OVERLAP = 150

_LANGCHAIN_LANG = {
    "python": Language.PYTHON, "js": Language.JS, "ts": Language.TS,
    "java": Language.JAVA, "go": Language.GO, "rust": Language.RUST,
    "ruby": Language.RUBY, "c": Language.C, "cpp": Language.CPP,
    "csharp": Language.CSHARP, "php": Language.PHP, "kotlin": Language.KOTLIN,
    "swift": Language.SWIFT, "scala": Language.SCALA, "markdown": Language.MARKDOWN,
    "html": Language.HTML,
}


@dataclass
class Chunk:
    text: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    metadata: dict = field(default_factory=dict)


def _splitter_for(language: str) -> RecursiveCharacterTextSplitter:
    lc_lang = _LANGCHAIN_LANG.get(language)
    if lc_lang is not None:
        return RecursiveCharacterTextSplitter.from_language(
            lc_lang, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
        )
    return RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)


def split_file(f: SourceFile) -> list[Chunk]:
    pieces = _splitter_for(f.language).split_text(f.content)
    chunks: list[Chunk] = []
    cursor = 0
    for piece in pieces:
        # locate the piece to compute real line numbers (overlap-safe: search from cursor)
        idx = f.content.find(piece, cursor)
        if idx == -1:
            idx = f.content.find(piece)
        start_line = f.content.count("\n", 0, idx) + 1
        end_line = start_line + piece.count("\n")
        cursor = idx + 1
        chunks.append(Chunk(
            text=piece, file_path=f.path, language=f.language,
            start_line=start_line, end_line=end_line,
        ))
    return chunks


def split_files(files: list[SourceFile]) -> list[Chunk]:
    out: list[Chunk] = []
    for f in files:
        out.extend(split_file(f))
    return out
