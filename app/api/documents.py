import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.document import Document
from app.schemas.document import DocumentOut, ExtractResponse, SummaryResponse
from app.services.document_processor import processor
from app.services.formatters import document_to_ui

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentOut)
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    settings = get_settings()
    document_id = str(uuid.uuid4())
    safe_name = Path(file.filename).name
    file_path = settings.upload_dir / f"{document_id}-{safe_name}"
    with file_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    document = Document(
        id=document_id,
        title=safe_name.rsplit(".", 1)[0],
        file_name=safe_name,
        file_path=str(file_path),
        size_bytes=file_path.stat().st_size,
        summary="DocuMind is indexing this file. Summary, citations, and extracted fields will appear after processing.",
        key_points=["Upload received", "Text extraction started", "Vector index pending"],
        fields={"Owner": "Pending", "Type": "PDF", "Confidence": "Pending"},
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        pages, page_count = processor.extract_pdf_text(file_path)
        chunks = processor.chunk_pages(pages)
        document.pages = page_count
        processor.index_document(db, document, chunks)
        db.refresh(document)
    except Exception as exc:
        document.status = "Needs review"
        document.summary = f"PDF upload succeeded, but processing failed: {exc}"
        document.key_points = ["Upload received", "Processing failed", "Review the PDF text layer"]
        document.fields = {"Type": "PDF", "Confidence": "Needs review"}
        db.commit()
        db.refresh(document)

    return document_to_ui(document)


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    documents = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [document_to_ui(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document_to_ui(document)


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    file_path = Path(document.file_path)
    if file_path.exists():
        file_path.unlink()
    processor.delete_index(document_id)
    db.delete(document)
    db.commit()
    return {"ok": True}


@router.post("/{document_id}/summary", response_model=SummaryResponse)
def summarize_document(document_id: str, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"summary": document.summary, "keyPoints": document.key_points or []}


@router.post("/{document_id}/extract", response_model=ExtractResponse)
def extract_document(document_id: str, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"fields": document.fields or {}}
