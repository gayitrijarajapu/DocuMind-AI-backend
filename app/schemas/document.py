from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class Source(BaseModel):
    page: int
    label: str


class DocumentOut(BaseModel):
    id: str
    title: str
    fileName: str
    uploadedAt: str
    status: str
    size: str
    pages: int
    category: str
    summary: str
    keyPoints: list[str]
    fields: dict[str, str]


class AskRequest(BaseModel):
    question: str
    document_id: Optional[str] = None
    session_id: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    sources: list[Source] = []
    session_id: str


class SummaryResponse(BaseModel):
    summary: str
    keyPoints: list[str]


class ExtractResponse(BaseModel):
    fields: dict[str, str]


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: list[Source] = []
    createdAt: str
    model_config = ConfigDict(from_attributes=True)


class DashboardStats(BaseModel):
    documents: int
    indexed: int
    aiAnswers: int
    processing: int
