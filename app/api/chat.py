from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import ChatMessage, Document
from app.schemas.document import AskRequest, AskResponse, ChatMessageOut
from app.services.qa import answer_question

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/ask", response_model=AskResponse)
def ask_question(payload: AskRequest, db: Session = Depends(get_db)):
    document_id = payload.document_id
    if not document_id:
        raise HTTPException(status_code=400, detail="document_id is required.")
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return answer_question(db, document, payload.question, payload.session_id)


@router.post("/documents/{document_id}", response_model=AskResponse)
def ask_document(document_id: str, payload: AskRequest, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return answer_question(db, document, payload.question, payload.session_id)


@router.get("/{session_id}", response_model=list[ChatMessageOut])
def get_chat_history(session_id: str, db: Session = Depends(get_db)):
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        {
            "id": str(message.id),
            "role": message.role,
            "content": message.content,
            "sources": message.sources or [],
            "createdAt": message.created_at.strftime("%I:%M %p").lstrip("0"),
        }
        for message in messages
    ]
