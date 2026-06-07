from dataclasses import dataclass, field
from pathlib import Path

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
        if not text:
            continue

        page_metadata = dict(metadata)
        page_metadata["page_number"] = page_index
        pages.append(
            LoadedPage(text=text, page_number=page_index, metadata=page_metadata)
        )

    return pages


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
