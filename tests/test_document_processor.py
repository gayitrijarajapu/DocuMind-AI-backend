import numpy as np
import pytest
import sys

from app.services.document_processor import DocumentProcessingError, DocumentProcessor, TextChunk


def test_document_processor_does_not_import_faiss_early():
    assert "faiss" not in sys.modules


def test_index_document_rejects_empty_chunks():
    processor = DocumentProcessor()

    with pytest.raises(DocumentProcessingError, match="No selectable text"):
        processor.index_document(None, None, [])


def test_encode_chunks_uses_configured_device(monkeypatch):
    processor = DocumentProcessor()
    processor.settings.embedding_device = "cpu"
    captured = {}

    class FakeEmbeddingModel:
        def encode(self, texts, **kwargs):
            captured["texts"] = texts
            captured["kwargs"] = kwargs
            return np.array([[0.1, 0.2, 0.3]], dtype="float32")

    processor._embedding_model = FakeEmbeddingModel()

    embeddings = processor._encode_chunks([TextChunk(page=1, chunk_index=0, text="hello")])

    assert embeddings.shape == (1, 3)
    assert captured["texts"] == ["hello"]
    assert captured["kwargs"]["device"] == "cpu"
    assert captured["kwargs"]["convert_to_numpy"] is True


def test_encode_chunks_wraps_embedding_errors():
    processor = DocumentProcessor()

    class BrokenEmbeddingModel:
        def encode(self, *args, **kwargs):
            raise RuntimeError("Cannot copy out of meta tensor")

    processor._embedding_model = BrokenEmbeddingModel()

    with pytest.raises(DocumentProcessingError, match="Embedding generation failed"):
        processor._encode_chunks([TextChunk(page=1, chunk_index=0, text="hello")])
