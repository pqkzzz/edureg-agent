from pathlib import Path
import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.ingestion.chunker import chunk_text
from app.ingestion.loaders import load_document


def calculate_file_hash(file_path: str | Path) -> str:
    path = Path(file_path)
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def ingest_document(
    db: Session,
    file_path: str | Path,
    title: str | None = None,
    school: str | None = None,
    faculty: str | None = None,
    program: str | None = None,
    cohort: str | None = None,
    document_type: str | None = None,
    effective_year: int | None = None,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> Document:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    content_hash = calculate_file_hash(path)
    existing_document = db.scalar(
        select(Document).where(Document.content_hash == content_hash)
    )
    if existing_document is not None:
        return existing_document

    document = Document(
        title=title or path.stem,
        filename=path.name,
        file_type=path.suffix.lower().lstrip("."),
        school=school,
        faculty=faculty,
        program=program,
        cohort=cohort,
        document_type=document_type,
        effective_year=effective_year,
        content_hash=content_hash,
        status="processing",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        loaded_pages = load_document(path)
        next_chunk_index = 0

        for page in loaded_pages:
            page_metadata = {
                **page.metadata,
                "document_title": document.title,
                "document_id": document.id,
                "school": school,
                "faculty": faculty,
                "program": program,
                "cohort": cohort,
                "document_type": document_type,
                "effective_year": effective_year,
            }
            chunks = chunk_text(
                page.text,
                chunk_size=chunk_size,
                overlap=overlap,
                page_number=page.page_number,
                metadata=page_metadata,
            )

            for chunk in chunks:
                db.add(
                    Chunk(
                        document_id=document.id,
                        chunk_index=next_chunk_index,
                        content=chunk.content,
                        page_number=chunk.page_number,
                        section_title=chunk.section_title,
                        token_count=chunk.token_count,
                        chunk_metadata=chunk.metadata,
                    )
                )
                next_chunk_index += 1

        if next_chunk_index == 0:
            raise ValueError("Document did not produce any chunks")

        document.status = "ready"
        db.commit()
        db.refresh(document)
        return document
    except Exception:
        db.rollback()
        document = db.merge(document)
        document.status = "failed"
        db.commit()
        raise
