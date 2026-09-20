import pytest

from app.models.document import Document
from app.services.document_processor import TextChunk
from app.services.gemini import GeminiServiceError, _parse_json_object
from app.services.qa import _generate_document_answer, _sources_from_chunks


def test_parse_json_object_handles_fenced_json():
    parsed = _parse_json_object('```json\n{"summary":"Done","keyPoints":["A"]}\n```')

    assert parsed["summary"] == "Done"
    assert parsed["keyPoints"] == ["A"]


def test_parse_json_object_rejects_non_json():
    with pytest.raises(GeminiServiceError):
        _parse_json_object("not-json")


def test_qa_falls_back_without_gemini(monkeypatch):
    document = Document(
        id="doc-1",
        title="Demo",
        file_name="demo.pdf",
        file_path="/tmp/demo.pdf",
        size_bytes=100,
        pages=2,
    )
    chunks = [TextChunk(page=2, chunk_index=0, text="This document explains demo findings.")]

    def fail_answer(*args, **kwargs):
        raise GeminiServiceError("missing key")

    monkeypatch.setattr("app.services.qa.gemini_service.answer_question", fail_answer)

    answer = _generate_document_answer(document, "What is it about?", chunks)

    assert "demo.pdf" in answer
    assert "page 2" in answer
    assert "demo findings" in answer


def test_sources_include_document_name_and_page():
    document = Document(
        id="doc-1",
        title="Demo",
        file_name="demo.pdf",
        file_path="/tmp/demo.pdf",
        size_bytes=100,
        pages=2,
    )
    chunks = [TextChunk(page=2, chunk_index=3, text="Chunk text")]

    sources = _sources_from_chunks(document, chunks)

    assert sources == [{"page": 2, "label": "demo.pdf · Chunk 4", "text": "Chunk text"}]
