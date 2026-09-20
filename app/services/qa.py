from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.document import ChatMessage, Document
from app.services.document_processor import TextChunk, processor
from app.services.gemini import gemini_service


def answer_question(db: Session, document: Document, question: str, session_id: str | None = None) -> dict:
    session_id = session_id or str(uuid.uuid4())
    chunks = processor.retrieve(document.id, question)
    answer = _generate_document_answer(document, question, chunks)
    sources = _sources_from_chunks(document, chunks)

    db.add(ChatMessage(session_id=session_id, document_id=document.id, role="user", content=question))
    db.add(
        ChatMessage(
            session_id=session_id,
            document_id=document.id,
            role="assistant",
            content=answer,
            sources=sources,
        )
    )
    db.commit()
    return {"answer": answer, "sources": sources, "session_id": session_id}


def _generate_document_answer(document: Document, question: str, chunks: list[TextChunk]) -> str:
    if not chunks:
        return "I could not find indexed text for this document yet. Try uploading a text-based PDF."

    try:
        return gemini_service.answer_question(document, question, chunks)
    except Exception:
        pass

    excerpt = chunks[0].text[:700].strip()
    return (
        f"Based on {document.file_name}, the most relevant passage is on page {chunks[0].page}: "
        f"{excerpt}"
    )


def _sources_from_chunks(document: Document, chunks: list[TextChunk]) -> list[dict]:
    seen = set()
    sources = []
    for chunk in chunks:
        key = (chunk.page, chunk.chunk_index)
        if key in seen:
            continue
        seen.add(key)
        excerpt = " ".join(chunk.text.split())[:240]
        sources.append(
            {
                "page": chunk.page,
                "label": f"{document.file_name} · Chunk {chunk.chunk_index + 1}",
                "text": excerpt,
            }
        )
    return sources[:4]
