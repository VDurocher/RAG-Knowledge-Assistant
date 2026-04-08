"""FAISS index construction and management (embeddings + persistence + incremental)."""

import hashlib
import json
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.config import Settings


def _get_embeddings(settings: Settings):
    """Instantiates the embeddings model according to configuration."""
    if settings.embedder_type == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.openai_api_key,
        )

    # Local mode: sentence-transformers via HuggingFace (free, offline)
    from langchain_community.embeddings import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=settings.local_embed_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def _compute_manifest(documents: list[Document]) -> str:
    """Computes a global hash representing the current state of documents (sources + content)."""
    sorted_docs = sorted(documents, key=lambda d: d.metadata.get("source", ""))
    fingerprint = "".join(
        f"{d.metadata.get('source', '')}:{d.page_content}"
        for d in sorted_docs
    )
    return hashlib.sha256(fingerprint.encode()).hexdigest()


def _compute_file_hashes(documents: list[Document]) -> dict[str, str]:
    """Computes a SHA-256 hash per source file for incremental detection."""
    file_docs: dict[str, list[str]] = {}
    for doc in documents:
        source = doc.metadata.get("source", "")
        file_docs.setdefault(source, []).append(doc.page_content)
    return {
        source: hashlib.sha256("".join(pages).encode()).hexdigest()
        for source, pages in file_docs.items()
    }


def _load_manifest(vector_store_path: Path) -> dict:
    """Loads the full manifest (global hash + per-file hashes)."""
    manifest_file = vector_store_path / "manifest.json"
    if not manifest_file.exists():
        return {"hash": "", "files": {}}
    try:
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        # Compatibility with old format (hash only)
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
    """Saves the manifest after a build or incremental update."""
    manifest_file = vector_store_path / "manifest.json"
    manifest_file.write_text(
        json.dumps({"hash": global_hash, "files": file_hashes}),
        encoding="utf-8",
    )


def split_documents(
    documents: list[Document], chunk_size: int, chunk_overlap: int
) -> list[Document]:
    """Splits documents into chunks of controlled size."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        # Hierarchical separators: paragraph → sentence → word
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(documents)


def build_index(documents: list[Document], settings: Settings) -> FAISS:
    """
    Creates a new full FAISS index from the provided documents.

    Saves the index and manifest to disk.
    """
    if not documents:
        raise ValueError("No documents loaded. Add files to knowledge_base/.")

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
    Loads the index from disk if available and up to date, rebuilds otherwise.

    Incremental strategy:
    - Additions only → targeted insert into existing index (fast)
    - Modification or deletion → full rebuild (only safe option with FAISS)
    - force_rebuild=True → always rebuild

    Returns:
        FAISS index ready to use.
    """
    embeddings = _get_embeddings(settings)
    index_file = settings.vector_store_path / "index.faiss"

    if force_rebuild or not index_file.exists():
        return build_index(documents, settings)

    manifest = _load_manifest(settings.vector_store_path)
    current_hash = _compute_manifest(documents)

    # Index already up to date
    if manifest["hash"] == current_hash:
        # SECURITY WARNING: allow_dangerous_deserialization enables FAISS pickle
        # deserialisation, which can execute arbitrary code if the index is compromised.
        # Risk accepted here because the index is generated and stored locally by the
        # application itself — it never comes from an untrusted external source.
        return FAISS.load_local(
            str(settings.vector_store_path),
            embeddings,
            allow_dangerous_deserialization=True,
        )

    # Analyse which files changed
    current_file_hashes = _compute_file_hashes(documents)
    saved_file_hashes: dict[str, str] = manifest.get("files", {})

    new_files = {k for k in current_file_hashes if k not in saved_file_hashes}
    removed_files = {k for k in saved_file_hashes if k not in current_file_hashes}
    modified_files = {
        k for k, v in current_file_hashes.items()
        if k in saved_file_hashes and saved_file_hashes[k] != v
    }

    # Favourable case: additions only → incremental indexing
    if new_files and not removed_files and not modified_files:
        # SECURITY WARNING: see comment above — same justification.
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

    # General case: modification or deletion → full rebuild
    return build_index(documents, settings)
