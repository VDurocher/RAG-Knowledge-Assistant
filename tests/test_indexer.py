"""Tests unitaires pour l'indexation et la découpe de documents."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from core.indexer import _compute_manifest, split_documents


class TestSplitDocuments:
    def test_splits_long_document(self) -> None:
        long_text = "sentence. " * 200  # ~2000 chars
        docs = [Document(page_content=long_text, metadata={"source": "test.txt"})]

        chunks = split_documents(docs, chunk_size=500, chunk_overlap=50)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.page_content) <= 600  # Tolérance pour les séparateurs

    def test_preserves_metadata(self) -> None:
        docs = [Document(page_content="Short text.", metadata={"source": "doc.pdf", "page": 1})]
        chunks = split_documents(docs, chunk_size=1000, chunk_overlap=100)

        assert all(chunk.metadata["source"] == "doc.pdf" for chunk in chunks)

    def test_short_document_not_split(self) -> None:
        docs = [Document(page_content="Short.", metadata={"source": "tiny.txt"})]
        chunks = split_documents(docs, chunk_size=1000, chunk_overlap=100)

        assert len(chunks) == 1


class TestComputeManifest:
    def test_same_sources_same_hash(self) -> None:
        docs_a = [
            Document(page_content="Content A", metadata={"source": "a.txt"}),
            Document(page_content="Content B", metadata={"source": "b.txt"}),
        ]
        docs_b = [
            Document(page_content="Different content", metadata={"source": "a.txt"}),
            Document(page_content="Other content", metadata={"source": "b.txt"}),
        ]
        # Le hash est basé sur les noms de fichiers, pas le contenu
        assert _compute_manifest(docs_a) == _compute_manifest(docs_b)

    def test_different_sources_different_hash(self) -> None:
        docs_a = [Document(page_content="Content", metadata={"source": "a.txt"})]
        docs_b = [Document(page_content="Content", metadata={"source": "b.txt"})]

        assert _compute_manifest(docs_a) != _compute_manifest(docs_b)

    def test_empty_documents_consistent(self) -> None:
        assert _compute_manifest([]) == _compute_manifest([])
