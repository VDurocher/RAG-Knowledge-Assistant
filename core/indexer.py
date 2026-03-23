"""Construction et gestion de l'index FAISS (embeddings + persistance + incrémental)."""

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
    """Calcule un hash global représentant l'état actuel des documents (sources + contenu)."""
    sorted_docs = sorted(documents, key=lambda d: d.metadata.get("source", ""))
    fingerprint = "".join(
        f"{d.metadata.get('source', '')}:{d.page_content}"
        for d in sorted_docs
    )
    return hashlib.sha256(fingerprint.encode()).hexdigest()


def _compute_file_hashes(documents: list[Document]) -> dict[str, str]:
    """Calcule un hash SHA-256 par fichier source pour la détection incrémentale."""
    file_docs: dict[str, list[str]] = {}
    for doc in documents:
        source = doc.metadata.get("source", "")
        file_docs.setdefault(source, []).append(doc.page_content)
    return {
        source: hashlib.sha256("".join(pages).encode()).hexdigest()
        for source, pages in file_docs.items()
    }


def _load_manifest(vector_store_path: Path) -> dict:
    """Charge le manifest complet (hash global + hashes par fichier)."""
    manifest_file = vector_store_path / "manifest.json"
    if not manifest_file.exists():
        return {"hash": "", "files": {}}
    try:
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        # Compatibilité avec l'ancien format (hash seulement)
        if "files" not in data:
            data["files"] = {}
        return data
    except Exception:
        return {"hash": "", "files": {}}


def _save_manifest(
    vector_store_path: Path,
    global_hash: str,
    file_hashes: dict[str, str],
) -> None:
    """Sauvegarde le manifest après un build ou une mise à jour incrémentale."""
    manifest_file = vector_store_path / "manifest.json"
    manifest_file.write_text(
        json.dumps({"hash": global_hash, "files": file_hashes}),
        encoding="utf-8",
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
    Crée un nouvel index FAISS complet à partir des documents fournis.

    Sauvegarde l'index et le manifest sur disque.
    """
    if not documents:
        raise ValueError("Aucun document chargé. Ajoutez des fichiers dans knowledge_base/.")

    chunks = split_documents(documents, settings.chunk_size, settings.chunk_overlap)
    embeddings = _get_embeddings(settings)

    vector_store = FAISS.from_documents(chunks, embeddings)

    settings.vector_store_path.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(settings.vector_store_path))
    _save_manifest(
        settings.vector_store_path,
        _compute_manifest(documents),
        _compute_file_hashes(documents),
    )

    return vector_store


def load_or_build_index(
    documents: list[Document], settings: Settings, force_rebuild: bool = False
) -> FAISS:
    """
    Charge l'index depuis le disque si disponible et à jour, reconstruit sinon.

    Stratégie incrémentale :
    - Seulement des ajouts → ajout ciblé dans l'index existant (rapide)
    - Modification ou suppression → rebuild complet (seule option sûre avec FAISS)
    - force_rebuild=True → rebuild systématique

    Returns:
        Index FAISS prêt à l'emploi.
    """
    embeddings = _get_embeddings(settings)
    index_file = settings.vector_store_path / "index.faiss"

    if force_rebuild or not index_file.exists():
        return build_index(documents, settings)

    manifest = _load_manifest(settings.vector_store_path)
    current_hash = _compute_manifest(documents)

    # Index déjà à jour
    if manifest["hash"] == current_hash:
        return FAISS.load_local(
            str(settings.vector_store_path),
            embeddings,
            allow_dangerous_deserialization=True,
        )

    # Analyser quels fichiers ont changé
    current_file_hashes = _compute_file_hashes(documents)
    saved_file_hashes: dict[str, str] = manifest.get("files", {})

    new_files = {k for k in current_file_hashes if k not in saved_file_hashes}
    removed_files = {k for k in saved_file_hashes if k not in current_file_hashes}
    modified_files = {
        k for k, v in current_file_hashes.items()
        if k in saved_file_hashes and saved_file_hashes[k] != v
    }

    # Cas favorable : seulement des ajouts → indexation incrémentale
    if new_files and not removed_files and not modified_files:
        vector_store = FAISS.load_local(
            str(settings.vector_store_path),
            embeddings,
            allow_dangerous_deserialization=True,
        )
        new_docs = [d for d in documents if d.metadata.get("source") in new_files]
        new_chunks = split_documents(new_docs, settings.chunk_size, settings.chunk_overlap)
        vector_store.add_documents(new_chunks)
        vector_store.save_local(str(settings.vector_store_path))
        _save_manifest(settings.vector_store_path, current_hash, current_file_hashes)
        return vector_store

    # Cas général : modification ou suppression → rebuild complet
    return build_index(documents, settings)
