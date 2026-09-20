from __future__ import annotations

import uuid

from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import ChatMessage, Document
from app.services.document_processor import TextChunk, processor


def answer_question(db: Session, document: Document, question: str, session_id: str | None = None) -> dict:
    session_id = session_id or str(uuid.uuid4())
    chunks = processor.retrieve(document.id, question)
    answer = _generate_answer(question, chunks)
    sources = _sources_from_chunks(chunks)

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


def _generate_answer(question: str, chunks: list[TextChunk]) -> str:
    if not chunks:
        return "I could not find indexed text for this document yet. Try uploading a text-based PDF."

    settings = get_settings()
    context = "\n\n".join(f"Page {chunk.page}: {chunk.text}" for chunk in chunks)
    if settings.openai_api_key:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Answer using only the provided PDF context. Be concise and mention page evidence.",
                ),
                ("human", "Question: {question}\n\nContext:\n{context}"),
            ]
        )
        chain = prompt | ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.2,
        )
        return chain.invoke({"question": question, "context": context}).content

    excerpt = chunks[0].text[:700].strip()
    return f"Based on the indexed PDF text, the most relevant passage is on page {chunks[0].page}: {excerpt}"


def _sources_from_chunks(chunks: list[TextChunk]) -> list[dict]:
    seen = set()
    sources = []
    for chunk in chunks:
        key = (chunk.page, chunk.chunk_index)
        if key in seen:
            continue
        seen.add(key)
        sources.append({"page": chunk.page, "label": f"Chunk {chunk.chunk_index + 1}"})
    return sources[:4]
