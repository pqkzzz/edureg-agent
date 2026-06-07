from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.db.session import get_db
from app.ingestion.pipeline import ingest_document


router = APIRouter(prefix="/documents", tags=["documents"])


class IngestLocalRequest(BaseModel):
    file_path: str
    title: str | None = None
    school: str | None = None
    faculty: str | None = None
    program: str | None = None
    cohort: str | None = None
    document_type: str | None = None
    effective_year: int | None = None
    chunk_size: int = Field(default=1200, gt=0)
    overlap: int = Field(default=200, ge=0)


class DocumentResponse(BaseModel):
    id: int
    title: str
    filename: str
    file_type: str
    school: str | None
    faculty: str | None
    program: str | None
    cohort: str | None
    document_type: str | None
    effective_year: int | None
    status: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class ChunkResponse(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    page_number: int | None
    section_title: str | None
    token_count: int
    chunk_metadata: dict
    created_at: datetime


def _document_to_response(document: Document, chunk_count: int) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        title=document.title,
        filename=document.filename,
        file_type=document.file_type,
        school=document.school,
        faculty=document.faculty,
        program=document.program,
        cohort=document.cohort,
        document_type=document.document_type,
        effective_year=document.effective_year,
        status=document.status,
        chunk_count=chunk_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _chunk_to_response(chunk: Chunk) -> ChunkResponse:
    return ChunkResponse(
        id=chunk.id,
        document_id=chunk.document_id,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        page_number=chunk.page_number,
        section_title=chunk.section_title,
        token_count=chunk.token_count,
        chunk_metadata=chunk.chunk_metadata,
        created_at=chunk.created_at,
    )


@router.post("/ingest-local", response_model=DocumentResponse)
def ingest_local_document(
    request: IngestLocalRequest, db: Session = Depends(get_db)
) -> DocumentResponse:
    if request.overlap >= request.chunk_size:
        raise HTTPException(
            status_code=400, detail="overlap must be smaller than chunk_size"
        )

    try:
        document = ingest_document(
            db=db,
            file_path=request.file_path,
            title=request.title,
            school=request.school,
            faculty=request.faculty,
            program=request.program,
            cohort=request.cohort,
            document_type=request.document_type,
            effective_year=request.effective_year,
            chunk_size=request.chunk_size,
            overlap=request.overlap,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    chunk_count = db.scalar(
        select(func.count()).select_from(Chunk).where(Chunk.document_id == document.id)
    )
    return _document_to_response(document, chunk_count or 0)


@router.get("", response_model=list[DocumentResponse])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentResponse]:
    documents = db.scalars(select(Document).order_by(Document.created_at.desc())).all()
    responses: list[DocumentResponse] = []

    for document in documents:
        chunk_count = db.scalar(
            select(func.count())
            .select_from(Chunk)
            .where(Chunk.document_id == document.id)
        )
        responses.append(_document_to_response(document, chunk_count or 0))

    return responses


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)) -> DocumentResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_count = db.scalar(
        select(func.count()).select_from(Chunk).where(Chunk.document_id == document.id)
    )
    return _document_to_response(document, chunk_count or 0)


@router.get("/{document_id}/chunks", response_model=list[ChunkResponse])
def list_document_chunks(
    document_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[ChunkResponse]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = db.scalars(
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
        .offset(offset)
        .limit(limit)
    ).all()

    return [_chunk_to_response(chunk) for chunk in chunks]
