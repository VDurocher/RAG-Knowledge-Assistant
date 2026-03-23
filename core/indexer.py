"""Construction et gestion de l'index FAISS (embeddings + persistance)."""

import hashlib
import json
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.config import Settings


def _get_embeddings(settings: Settings):
    """Instancie le modèle d'embeddings selon la configuration."""
    if settings.embedder_type == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.openai_api_key,
        )

    # Mode local : sentence-transformers via HuggingFace (gratuit, offline)
    from langchain_community.embeddings import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=settings.local_embed_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def _compute_manifest(documents: list[Document]) -> str:
    """Calcule un hash représentant l'état actuel des documents (sources + contenu)."""
    # Trier par source pour un hash déterministe
    sorted_docs = sorted(documents, key=lambda d: d.metadata.get("source", ""))
    fingerprint = "".join(
        f"{d.metadata.get('source', '')}:{d.page_content}"
        for d in sorted_docs
    )
    return hashlib.md5(fingerprint.encode()).hexdigest()


def _load_manifest(vector_store_path: Path) -> str | None:
    """Charge le manifest sauvegardé (hash des sources au dernier build)."""
    manifest_file = vector_store_path / "manifest.json"
    if not manifest_file.exists():
        return None
    try:
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        return data.get("hash")
    except Exception:
        return None


def _save_manifest(vector_store_path: Path, manifest_hash: str) -> None:
    """Sauvegarde le manifest après un build réussi."""
    manifest_file = vector_store_path / "manifest.json"
    manifest_file.write_text(
        json.dumps({"hash": manifest_hash}), encoding="utf-8"
    )


def split_documents(
    documents: list[Document], chunk_size: int, chunk_overlap: int
) -> list[Document]:
    """Découpe les documents en chunks de taille contrôlée."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        # Séparateurs hiérarchiques : paragraphe → phrase → mot
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(documents)


def build_index(documents: list[Document], settings: Settings) -> FAISS:
    """
    Crée un nouvel index FAISS à partir des documents fournis.

    Le découpage en chunks et l'embedding sont effectués ici.
    L'index est sauvegardé sur disque pour les sessions suivantes.
    """
    if not documents:
        raise ValueError("Aucun document chargé. Ajoutez des fichiers dans knowledge_base/.")

    chunks = split_documents(documents, settings.chunk_size, settings.chunk_overlap)
    embeddings = _get_embeddings(settings)

    vector_store = FAISS.from_documents(chunks, embeddings)

    # Persistance sur disque
    settings.vector_store_path.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(settings.vector_store_path))
    _save_manifest(settings.vector_store_path, _compute_manifest(documents))

    return vector_store


def load_or_build_index(
    documents: list[Document], settings: Settings, force_rebuild: bool = False
) -> FAISS:
    """
    Charge l'index depuis le disque si disponible et à jour.
    Reconstruit si l'index est absent, obsolète ou si force_rebuild=True.

    Returns:
        Index FAISS prêt à l'emploi.
    """
    embeddings = _get_embeddings(settings)
    index_file = settings.vector_store_path / "index.faiss"
    current_hash = _compute_manifest(documents)

    index_exists = index_file.exists()
    index_is_fresh = _load_manifest(settings.vector_store_path) == current_hash

    if not force_rebuild and index_exists and index_is_fresh:
        return FAISS.load_local(
            str(settings.vector_store_path),
            embeddings,
            allow_dangerous_deserialization=True,
        )

    return build_index(documents, settings)
