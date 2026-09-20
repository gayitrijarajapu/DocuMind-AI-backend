from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import ChatMessage, Document
from app.schemas.document import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db)):
    return {
        "documents": db.query(Document).count(),
        "indexed": db.query(Document).filter(Document.status == "Indexed").count(),
        "aiAnswers": db.query(ChatMessage).filter(ChatMessage.role == "assistant").count(),
        "processing": db.query(Document).filter(Document.status == "Processing").count(),
    }
