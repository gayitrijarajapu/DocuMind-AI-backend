from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.services.document_processor import TextChunk, processor
from app.services.gemini import gemini_service


def load_document_chunks(db: Session, document_id: str) -> List[TextChunk]:
    rows = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )
    return [TextChunk(page=row.page, chunk_index=row.chunk_index, text=row.text) for row in rows]


def summarize_document(db: Session, document: Document) -> dict:
    chunks = load_document_chunks(db, document.id)
    try:
        result = gemini_service.summarize(document, chunks)
    except Exception:
        result = {
            "summary": processor.summary_from_chunks(chunks),
            "keyPoints": processor.key_points_from_chunks(chunks),
        }

    document.summary = result["summary"]
    document.key_points = result["keyPoints"] or processor.key_points_from_chunks(chunks)
    db.commit()
    db.refresh(document)
    return {"summary": document.summary, "keyPoints": document.key_points}


def extract_document_fields(db: Session, document: Document) -> dict:
    chunks = load_document_chunks(db, document.id)
    try:
        fields = gemini_service.extract_fields(document, chunks)
    except Exception:
        fields = processor.fields_from_document(document, chunks)

    document.fields = fields or processor.fields_from_document(document, chunks)
    db.commit()
    db.refresh(document)
    return {"fields": document.fields}
