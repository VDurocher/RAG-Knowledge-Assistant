"""Chargement des documents PDF, TXT, CSV, DOCX et JSON depuis knowledge_base."""

import logging
from pathlib import Path

from langchain_community.document_loaders import CSVLoader, PyPDFLoader, TextLoader
from langchain_core.documents import Document

# Logger structuré — remplace les print() interdits en production
_logger = logging.getLogger(__name__)

# Extensions texte — même logique de chargement (TextLoader ou loader dédié)
_TEXT_EXTENSIONS: dict[str, type] = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".md": TextLoader,
    ".json": TextLoader,  # JSON chargé comme texte brut
}
_SUPPORTED_EXTENSIONS = {**_TEXT_EXTENSIONS, ".csv": CSVLoader, ".docx": None}


def _load_csv(file_path: Path) -> list[Document]:
    """Charge un CSV : chaque ligne devient un Document avec toutes ses colonnes."""
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
    """Charge un DOCX via Docx2txtLoader (nécessite docx2txt)."""
    try:
        from langchain_community.document_loaders import Docx2txtLoader
    except ImportError:
        raise ImportError(
            "Le chargement DOCX nécessite docx2txt. Installez-le avec : pip install docx2txt"
        )
    loader = Docx2txtLoader(str(file_path))
    docs = loader.load()
    for doc in docs:
        doc.metadata["source"] = file_path.name
    return docs


def load_documents(knowledge_base_path: Path) -> list[Document]:
    """
    Charge tous les fichiers supportés du dossier spécifié.

    Formats acceptés : PDF, TXT, MD, CSV, DOCX, JSON.
    Chaque document reçoit metadata['source'] = nom du fichier pour les citations.

    Raises:
        FileNotFoundError: Si knowledge_base n'existe pas.
    """
    if not knowledge_base_path.exists():
        raise FileNotFoundError(
            f"Dossier introuvable: '{knowledge_base_path}'. "
            "Créez-le et ajoutez vos fichiers PDF/TXT/CSV/DOCX/JSON."
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
            _logger.warning("Impossible de charger '%s': %s", file_path.name, error)

    return documents


def list_source_files(knowledge_base_path: Path) -> list[str]:
    """Retourne la liste des fichiers supportés dans knowledge_base."""
    if not knowledge_base_path.exists():
        return []

    return [
        f.name
        for f in sorted(knowledge_base_path.rglob("*"))
        if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTENSIONS
    ]
