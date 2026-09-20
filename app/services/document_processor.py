from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document, DocumentChunk


@dataclass
class TextChunk:
    page: int
    chunk_index: int
    text: str


class DocumentProcessor:
    def __init__(self):
        self.settings = get_settings()
        self._embedding_model: SentenceTransformer | None = None

    @property
    def embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            model_name = self.settings.embedding_model.replace("sentence-transformers/", "")
            self._embedding_model = SentenceTransformer(model_name)
        return self._embedding_model

    def extract_pdf_text(self, file_path: Path) -> tuple[list[tuple[int, str]], int]:
        reader = PdfReader(str(file_path))
        pages: list[tuple[int, str]] = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append((index, re.sub(r"\s+", " ", text).strip()))
        return pages, len(reader.pages)

    def chunk_pages(self, pages: list[tuple[int, str]], chunk_size: int = 900, overlap: int = 160) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        chunk_index = 0
        for page, text in pages:
            if not text:
                continue
            start = 0
            while start < len(text):
                chunk_text = text[start : start + chunk_size].strip()
                if chunk_text:
                    chunks.append(TextChunk(page=page, chunk_index=chunk_index, text=chunk_text))
                    chunk_index += 1
                start += chunk_size - overlap
        return chunks

    def index_document(self, db: Session, document: Document, chunks: list[TextChunk]) -> None:
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
        db.add_all(
            DocumentChunk(
                document_id=document.id,
                page=chunk.page,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
            )
            for chunk in chunks
        )

        if chunks:
            embeddings = self.embedding_model.encode(
                [chunk.text for chunk in chunks], normalize_embeddings=True
            ).astype("float32")
            index = faiss.IndexFlatIP(embeddings.shape[1])
            index.add(embeddings)
            faiss.write_index(index, str(self._index_path(document.id)))
            self._metadata_path(document.id).write_text(
                json.dumps([chunk.__dict__ for chunk in chunks]), encoding="utf-8"
            )

        document.status = "Indexed" if chunks else "Needs review"
        document.key_points = self.key_points_from_chunks(chunks)
        document.summary = self.summary_from_chunks(chunks)
        document.fields = self.fields_from_document(document, chunks)
        db.commit()

    def retrieve(self, document_id: str, question: str, limit: int = 4) -> list[TextChunk]:
        index_path = self._index_path(document_id)
        metadata_path = self._metadata_path(document_id)
        if not index_path.exists() or not metadata_path.exists():
            return []

        index = faiss.read_index(str(index_path))
        chunks = [TextChunk(**item) for item in json.loads(metadata_path.read_text(encoding="utf-8"))]
        query = self.embedding_model.encode([question], normalize_embeddings=True).astype("float32")
        scores, indices = index.search(query, min(limit, len(chunks)))
        return [chunks[i] for i in indices[0] if i >= 0]

    def summary_from_chunks(self, chunks: list[TextChunk]) -> str:
        if not chunks:
            return "No selectable text could be extracted from this PDF."
        text = " ".join(chunk.text for chunk in chunks[:3])
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return " ".join(sentences[:3]).strip()[:900] or "Document indexed successfully."

    def key_points_from_chunks(self, chunks: list[TextChunk]) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", " ".join(chunk.text for chunk in chunks[:5]))
        points = [sentence.strip() for sentence in sentences if len(sentence.strip()) > 40]
        return points[:3] or ["Text extracted from PDF.", "Vector index created.", "Ready for questions."]

    def fields_from_document(self, document: Document, chunks: list[TextChunk]) -> dict[str, str]:
        return {
            "File": document.file_name,
            "Type": "PDF",
            "Pages": str(document.pages),
            "Chunks": str(len(chunks)),
            "Confidence": "Indexed" if chunks else "Needs review",
        }

    def _index_path(self, document_id: str) -> Path:
        return self.settings.faiss_dir / f"{document_id}.index"

    def _metadata_path(self, document_id: str) -> Path:
        return self.settings.faiss_dir / f"{document_id}.json"

    def delete_index(self, document_id: str) -> None:
        for path in (self._index_path(document_id), self._metadata_path(document_id)):
            if path.exists():
                path.unlink()


processor = DocumentProcessor()
