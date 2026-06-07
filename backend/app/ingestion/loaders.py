from dataclasses import dataclass, field
from pathlib import Path
import re

from app.ingestion.chunker import normalize_text


@dataclass
class LoadedPage:
    text: str
    page_number: int | None = None
    metadata: dict = field(default_factory=dict)


SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf", ".docx", ".html", ".htm"}


def load_document(file_path: str | Path) -> list[LoadedPage]:
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {extension}")
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    metadata = {"source": path.name, "file_type": extension.lstrip(".")}

    if extension in {".txt", ".md", ".markdown"}:
        return _load_text_file(path, metadata)
    if extension == ".pdf":
        return _load_pdf_file(path, metadata)
    if extension == ".docx":
        return _load_docx_file(path, metadata)
    if extension in {".html", ".htm"}:
        return _load_html_file(path, metadata)

    raise ValueError(f"Unsupported file type: {extension}")


def _load_text_file(path: Path, metadata: dict) -> list[LoadedPage]:
    text = path.read_text(encoding="utf-8")
    text = normalize_text(text)
    if not text:
        return []

    return [LoadedPage(text=text, metadata=dict(metadata))]


def _load_pdf_file(path: Path, metadata: dict) -> list[LoadedPage]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages: list[LoadedPage] = []

    for page_index, page in enumerate(reader.pages, start=1):
        text = normalize_text(page.extract_text() or "")
        text = _clean_pdf_formula_artifacts(text, page_number=page_index)
        if not text:
            continue

        page_metadata = dict(metadata)
        page_metadata["page_number"] = page_index
        pages.append(
            LoadedPage(text=text, page_number=page_index, metadata=page_metadata)
        )

    return pages


def _clean_pdf_formula_artifacts(text: str, page_number: int | None = None) -> str:
    def replace_formula_block(match: re.Match[str]) -> str:
        prefix = match.group("prefix")
        formula_block = match.group("formula")
        suffix = match.group("suffix")

        if not _looks_like_broken_formula(formula_block):
            return match.group(0)

        page_hint = f", trang {page_number}" if page_number is not None else ""
        placeholder = f"[Công thức toán học trong tài liệu gốc{page_hint}]"
        return f"{prefix}\n\n{placeholder}\n\n{suffix}"

    cleaned = re.sub(
        r"(?P<prefix>công thức sau:\s*)\n+(?P<formula>.*?)(?P<suffix>\nTrong đó:)",
        replace_formula_block,
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return normalize_text(cleaned)


def _looks_like_broken_formula(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False

    private_use_chars = sum(1 for char in text if "\uf000" <= char <= "\uf8ff")
    math_chars = sum(1 for char in text if char in "∑Σ=×*/+-")
    short_lines = sum(1 for line in lines if len(line) <= 6)

    return private_use_chars > 0 or (math_chars >= 2 and short_lines >= 3)


def _load_docx_file(path: Path, metadata: dict) -> list[LoadedPage]:
    from docx import Document as DocxDocument

    document = DocxDocument(str(path))
    paragraphs = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]
    text = normalize_text("\n".join(paragraphs))
    if not text:
        return []

    return [LoadedPage(text=text, metadata=dict(metadata))]


def _load_html_file(path: Path, metadata: dict) -> list[LoadedPage]:
    from bs4 import BeautifulSoup

    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    text = normalize_text(soup.get_text(separator="\n"))
    if not text:
        return []

    return [LoadedPage(text=text, metadata=dict(metadata))]
