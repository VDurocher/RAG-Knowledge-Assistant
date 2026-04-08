"""Unit tests for document indexing and splitting."""

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
            assert len(chunk.page_content) <= 600  # Tolerance for separators

    def test_preserves_metadata(self) -> None:
        docs = [Document(page_content="Short text.", metadata={"source": "doc.pdf", "page": 1})]
        chunks = split_documents(docs, chunk_size=1000, chunk_overlap=100)

        assert all(chunk.metadata["source"] == "doc.pdf" for chunk in chunks)

    def test_short_document_not_split(self) -> None:
        docs = [Document(page_content="Short.", metadata={"source": "tiny.txt"})]
        chunks = split_documents(docs, chunk_size=1000, chunk_overlap=100)

        assert len(chunks) == 1


class TestComputeManifest:
    def test_same_input_different_order_same_hash(self) -> None:
        """Documents sorted by source — order in the input list must not matter."""
        docs_a = [
            Document(page_content="Content A", metadata={"source": "a.txt"}),
            Document(page_content="Content B", metadata={"source": "b.txt"}),
        ]
        docs_b = [
            Document(page_content="Content B", metadata={"source": "b.txt"}),
            Document(page_content="Content A", metadata={"source": "a.txt"}),
        ]
        assert _compute_manifest(docs_a) == _compute_manifest(docs_b)

    def test_different_content_different_hash(self) -> None:
        """Changing file content must produce a different manifest hash."""
        docs_a = [Document(page_content="Content A", metadata={"source": "a.txt"})]
        docs_b = [Document(page_content="Content B", metadata={"source": "a.txt"})]

        assert _compute_manifest(docs_a) != _compute_manifest(docs_b)

    def test_different_sources_different_hash(self) -> None:
        docs_a = [Document(page_content="Content", metadata={"source": "a.txt"})]
        docs_b = [Document(page_content="Content", metadata={"source": "b.txt"})]

        assert _compute_manifest(docs_a) != _compute_manifest(docs_b)

    def test_empty_documents_consistent(self) -> None:
        assert _compute_manifest([]) == _compute_manifest([])
