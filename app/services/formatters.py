from datetime import datetime

from app.models.document import Document


def human_size(size_bytes: int) -> str:
    mb = max(size_bytes / 1024 / 1024, 0.1)
    return f"{mb:.1f} MB"


def relative_date(value: datetime) -> str:
    today = datetime.utcnow().date()
    if value.date() == today:
        return "Today"
    return value.strftime("%b %d")


def document_to_ui(document: Document) -> dict:
    return {
        "id": document.id,
        "title": document.title,
        "fileName": document.file_name,
        "uploadedAt": relative_date(document.uploaded_at),
        "status": document.status,
        "size": human_size(document.size_bytes),
        "pages": document.pages,
        "category": document.category,
        "summary": document.summary,
        "keyPoints": document.key_points or [],
        "fields": {str(key): str(value) for key, value in (document.fields or {}).items()},
    }
