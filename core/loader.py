"""Loading PDF, TXT, CSV, DOCX and JSON documents from knowledge_base."""

import logging
from pathlib import Path

from langchain_community.document_loaders import CSVLoader, PyPDFLoader, TextLoader
from langchain_core.documents import Document

# Structured logger — replaces print() which is forbidden in production
_logger = logging.getLogger(__name__)

# Text extensions — same loading logic (TextLoader or dedicated loader)
_TEXT_EXTENSIONS: dict[str, type] = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".md": TextLoader,
    ".json": TextLoader,  # JSON loaded as raw text
}
_SUPPORTED_EXTENSIONS = {**_TEXT_EXTENSIONS, ".csv": CSVLoader, ".docx": None}


def _load_csv(file_path: Path) -> list[Document]:
    """Loads a CSV: each row becomes a Document with all its columns."""
    loader = CSVLoader(
        str(file_path),
        encoding="utf-8",
        csv_args={"delimiter": ","},
    )
    docs = loader.load()
    for doc in docs:
        doc.metadata["source"] = file_path.name
    return docs


def _load_docx(file_path: Path) -> list[Document]:
    """Loads a DOCX via Docx2txtLoader (requires docx2txt)."""
    try:
        from langchain_community.document_loaders import Docx2txtLoader
    except ImportError:
        raise ImportError(
            "Loading DOCX requires docx2txt. Install it with: pip install docx2txt"
        )
    loader = Docx2txtLoader(str(file_path))
    docs = loader.load()
    for doc in docs:
        doc.metadata["source"] = file_path.name
    return docs


def load_documents(knowledge_base_path: Path) -> list[Document]:
    """
    Loads all supported files from the specified folder.

    Accepted formats: PDF, TXT, MD, CSV, DOCX, JSON.
    Each document receives metadata['source'] = filename for citations.

    Raises:
        FileNotFoundError: If knowledge_base does not exist.
    """
    if not knowledge_base_path.exists():
        raise FileNotFoundError(
            f"Folder not found: '{knowledge_base_path}'. "
            "Create it and add your PDF/TXT/CSV/DOCX/JSON files."
        )

    documents: list[Document] = []

    for file_path in sorted(knowledge_base_path.rglob("*")):
        if not file_path.is_file():
            continue

        suffix = file_path.suffix.lower()

        try:
            if suffix == ".csv":
                docs = _load_csv(file_path)
            elif suffix == ".docx":
                docs = _load_docx(file_path)
            elif suffix in _TEXT_EXTENSIONS:
                loader_class = _TEXT_EXTENSIONS[suffix]
                if loader_class is TextLoader:
                    loader = loader_class(str(file_path), encoding="utf-8")
                else:
                    loader = loader_class(str(file_path))
                docs = loader.load()
                for doc in docs:
                    doc.metadata["source"] = file_path.name
            else:
                continue

            documents.extend(docs)

        except Exception as error:
            _logger.warning("Could not load '%s': %s", file_path.name, error)

    return documents


def list_source_files(knowledge_base_path: Path) -> list[str]:
    """Returns the list of supported files in knowledge_base."""
    if not knowledge_base_path.exists():
        return []

    return [
        f.name
        for f in sorted(knowledge_base_path.rglob("*"))
        if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTENSIONS
    ]
