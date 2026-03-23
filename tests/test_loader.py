"""Tests unitaires pour le chargement des documents."""

import tempfile
from pathlib import Path

import pytest

from core.loader import list_source_files, load_documents


@pytest.fixture
def temp_knowledge_base(tmp_path: Path) -> Path:
    """Crée un dossier temporaire avec des fichiers de test."""
    kb = tmp_path / "knowledge_base"
    kb.mkdir()

    (kb / "policy.txt").write_text(
        "Company policy: All employees must follow security protocols.", encoding="utf-8"
    )
    (kb / "guide.txt").write_text(
        "Onboarding guide: Welcome to the team. Please complete your setup.", encoding="utf-8"
    )
    (kb / "ignored.csv").write_text("col1,col2\nval1,val2", encoding="utf-8")

    return kb


class TestLoadDocuments:
    def test_loads_txt_files(self, temp_knowledge_base: Path) -> None:
        docs = load_documents(temp_knowledge_base)
        sources = {doc.metadata["source"] for doc in docs}

        assert "policy.txt" in sources
        assert "guide.txt" in sources

    def test_ignores_unsupported_extensions(self, temp_knowledge_base: Path) -> None:
        docs = load_documents(temp_knowledge_base)
        sources = {doc.metadata["source"] for doc in docs}

        assert "ignored.csv" not in sources

    def test_source_metadata_is_filename_only(self, temp_knowledge_base: Path) -> None:
        docs = load_documents(temp_knowledge_base)
        for doc in docs:
            assert "/" not in doc.metadata["source"]
            assert "\\" not in doc.metadata["source"]

    def test_raises_when_folder_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_documents(tmp_path / "nonexistent")

    def test_returns_empty_list_for_empty_folder(self, tmp_path: Path) -> None:
        empty_kb = tmp_path / "empty_kb"
        empty_kb.mkdir()
        docs = load_documents(empty_kb)
        assert docs == []


class TestListSourceFiles:
    def test_lists_supported_files(self, temp_knowledge_base: Path) -> None:
        files = list_source_files(temp_knowledge_base)
        assert "policy.txt" in files
        assert "guide.txt" in files

    def test_excludes_unsupported_files(self, temp_knowledge_base: Path) -> None:
        files = list_source_files(temp_knowledge_base)
        assert "ignored.csv" not in files

    def test_returns_empty_for_missing_folder(self, tmp_path: Path) -> None:
        files = list_source_files(tmp_path / "nonexistent")
        assert files == []
