from dataclasses import dataclass, field
import re


@dataclass
class TextChunk:
    chunk_index: int
    content: str
    token_count: int
    page_number: int | None = None
    section_title: str | None = None
    metadata: dict = field(default_factory=dict)


def estimate_token_count(text: str) -> int:
    return len(text.split())


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 200,
    page_number: int | None = None,
    section_title: str | None = None,
    metadata: dict | None = None,
) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0:
        raise ValueError("overlap must be greater than or equal to 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    normalized_text = normalize_text(text)
    if not normalized_text:
        return []

    chunks: list[TextChunk] = []
    start = 0
    chunk_metadata = metadata or {}

    while start < len(normalized_text):
        end = min(start + chunk_size, len(normalized_text))
        content = normalized_text[start:end].strip()

        if content:
            chunks.append(
                TextChunk(
                    chunk_index=len(chunks),
                    content=content,
                    token_count=estimate_token_count(content),
                    page_number=page_number,
                    section_title=section_title,
                    metadata=dict(chunk_metadata),
                )
            )

        if end == len(normalized_text):
            break

        start = end - overlap

    return chunks
