from __future__ import annotations

import json
import re
from functools import cached_property
from typing import Any, Dict, List

from langchain.prompts import ChatPromptTemplate

from app.core.config import get_settings
from app.models.document import Document
from app.services.document_processor import TextChunk


class GeminiServiceError(RuntimeError):
    pass


class GeminiService:
    @cached_property
    def llm(self):
        settings = get_settings()
        if not settings.gemini_api_key:
            raise GeminiServiceError("GEMINI_API_KEY is not configured.")

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:
            raise GeminiServiceError("langchain-google-genai is not installed.") from exc

        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.2,
        )

    def answer_question(self, document: Document, question: str, chunks: List[TextChunk]) -> str:
        if not chunks:
            return "I could not find indexed text for this document yet. Try uploading a text-based PDF."

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are DocuMind AI. Answer only from the provided document context. "
                    "Be concise, and include source document names and page numbers in the answer.",
                ),
                (
                    "human",
                    "Document: {document_name}\nQuestion: {question}\n\nContext:\n{context}",
                ),
            ]
        )
        chain = prompt | self.llm
        return chain.invoke(
            {
                "document_name": document.file_name,
                "question": question,
                "context": self._format_context(document, chunks),
            }
        ).content

    def summarize(self, document: Document, chunks: List[TextChunk]) -> Dict[str, Any]:
        if not chunks:
            return {
                "summary": "No selectable text could be extracted from this PDF.",
                "keyPoints": ["No extractable text found.", "Try a text-based PDF.", "Review the upload."],
            }

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Summarize the document. Return strict JSON with keys summary and keyPoints. "
                    "keyPoints must be an array of three concise strings.",
                ),
                (
                    "human",
                    "Document: {document_name}\nContext:\n{context}",
                ),
            ]
        )
        response = (prompt | self.llm).invoke(
            {
                "document_name": document.file_name,
                "context": self._format_context(document, chunks[:8]),
            }
        ).content
        data = _parse_json_object(response)
        return {
            "summary": str(data.get("summary") or document.summary),
            "keyPoints": [str(item) for item in data.get("keyPoints", [])][:5],
        }

    def extract_fields(self, document: Document, chunks: List[TextChunk]) -> Dict[str, str]:
        if not chunks:
            return document.fields or {}

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Extract important structured fields from the document. Return strict JSON only. "
                    "Use short string values. Include Source Document and Source Pages.",
                ),
                (
                    "human",
                    "Document: {document_name}\nContext:\n{context}",
                ),
            ]
        )
        response = (prompt | self.llm).invoke(
            {
                "document_name": document.file_name,
                "context": self._format_context(document, chunks[:8]),
            }
        ).content
        data = _parse_json_object(response)
        return {str(key): str(value) for key, value in data.items()}

    def _format_context(self, document: Document, chunks: List[TextChunk]) -> str:
        return "\n\n".join(
            f"Source: {document.file_name}\nPage: {chunk.page}\nChunk: {chunk.chunk_index + 1}\nText: {chunk.text}"
            for chunk in chunks
        )


def _parse_json_object(value: str) -> Dict[str, Any]:
    cleaned = value.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GeminiServiceError("Gemini returned non-JSON content.") from exc
    if not isinstance(parsed, dict):
        raise GeminiServiceError("Gemini returned JSON that is not an object.")
    return parsed


gemini_service = GeminiService()
