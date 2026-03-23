"""Chargement des documents PDF et TXT depuis le dossier knowledge_base."""

from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

# Extensions supportées et leur loader associé
_SUPPORTED_EXTENSIONS: dict[str, type] = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".md": TextLoader,
}


def load_documents(knowledge_base_path: Path) -> list[Document]:
    """
    Charge tous les fichiers PDF/TXT/MD du dossier spécifié.

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
            "Créez-le et ajoutez vos fichiers PDF/TXT."
        )

    documents: list[Document] = []

    for file_path in sorted(knowledge_base_path.rglob("*")):
        if not file_path.is_file():
            continue

        loader_class = _SUPPORTED_EXTENSIONS.get(file_path.suffix.lower())
        if loader_class is None:
            continue

        try:
            if loader_class is TextLoader:
                loader = loader_class(str(file_path), encoding="utf-8")
            else:
                loader = loader_class(str(file_path))

            docs = loader.load()

            # Normaliser la source pour les citations : nom de fichier uniquement
            for doc in docs:
                doc.metadata["source"] = file_path.name

            documents.extend(docs)

        except Exception as error:
            # Loguer l'erreur sans interrompre le chargement des autres fichiers
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
