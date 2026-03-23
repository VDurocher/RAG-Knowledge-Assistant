"""Chargement des documents PDF, TXT et CSV depuis le dossier knowledge_base."""

from pathlib import Path

from langchain_community.document_loaders import CSVLoader, PyPDFLoader, TextLoader
from langchain_core.documents import Document

# Extensions supportées — le CSV est traité à part (logique différente)
_TEXT_EXTENSIONS: dict[str, type] = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".md": TextLoader,
}
_SUPPORTED_EXTENSIONS = {**_TEXT_EXTENSIONS, ".csv": CSVLoader}


def _load_csv(file_path: Path) -> list[Document]:
    """
    Charge un CSV : chaque ligne devient un Document avec toutes ses colonnes.
    Le contenu est formaté lisiblement pour le retrieval.
    """
    loader = CSVLoader(
        str(file_path),
        encoding="utf-8",
        csv_args={"delimiter": ","},
    )
    docs = loader.load()
    for doc in docs:
        doc.metadata["source"] = file_path.name
    return docs


def load_documents(knowledge_base_path: Path) -> list[Document]:
    """
    Charge tous les fichiers PDF/TXT/MD/CSV du dossier spécifié.

    Chaque document reçoit un metadata['source'] avec le nom du fichier
    pour permettre les citations dans les réponses.

    Returns:
        Liste de Document LangChain avec metadata['source'] normalisé.

    Raises:
        FileNotFoundError: Si le dossier knowledge_base n'existe pas.
    """
    if not knowledge_base_path.exists():
        raise FileNotFoundError(
            f"Dossier introuvable: '{knowledge_base_path}'. "
            "Créez-le et ajoutez vos fichiers PDF/TXT/CSV."
        )

    documents: list[Document] = []

    for file_path in sorted(knowledge_base_path.rglob("*")):
        if not file_path.is_file():
            continue

        suffix = file_path.suffix.lower()

        try:
            if suffix == ".csv":
                docs = _load_csv(file_path)
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
            print(f"[loader] Impossible de charger '{file_path.name}': {error}")

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
