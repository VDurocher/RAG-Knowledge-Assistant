"""Centralised configuration — loaded from environment variables."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from .env."""

    # Embeddings: "openai" (paid, higher quality) or "local" (HuggingFace, free)
    embedder_type: str = field(
        default_factory=lambda: os.getenv("EMBEDDER_TYPE", "local")
    )

    # Generation engine: "openai" (cloud) or "ollama" (local, free)
    llm_type: str = field(
        default_factory=lambda: os.getenv("LLM_TYPE", "openai")
    )

    # OpenAI API key — required only if llm_type="openai" (or embedder_type="openai")
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )

    # OpenAI generation model
    openai_chat_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    )

    # Ollama configuration (fully local, free)
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2")
    )

    # HuggingFace model for local embeddings
    local_embed_model: str = field(
        default_factory=lambda: os.getenv(
            "LOCAL_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
    )

    # Text splitting parameters
    chunk_size: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_SIZE", "1000"))
    )
    chunk_overlap: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "200"))
    )

    # Number of documents retrieved per query
    retrieval_k: int = field(
        default_factory=lambda: int(os.getenv("RETRIEVAL_K", "4"))
    )

    # Minimum confidence threshold (0.0 = disabled) — filters irrelevant docs
    retrieval_score_threshold: float = field(
        default_factory=lambda: float(os.getenv("RETRIEVAL_SCORE_THRESHOLD", "0.3"))
    )

    # Hybrid BM25 + semantic search (requires rank-bm25)
    hybrid_search: bool = field(
        default_factory=lambda: os.getenv("HYBRID_SEARCH", "false").lower() == "true"
    )

    # BM25 weight in hybrid search (0.4 = 40% lexical, 60% semantic)
    bm25_weight: float = field(
        default_factory=lambda: float(os.getenv("BM25_WEIGHT", "0.4"))
    )

    # Folder paths
    knowledge_base_path: Path = field(default_factory=lambda: Path("knowledge_base"))
    vector_store_path: Path = field(default_factory=lambda: Path("vector_store"))

    def validate(self) -> None:
        """Validates the configuration before startup."""
        if self.llm_type not in {"openai", "ollama"}:
            raise ValueError(
                f"Invalid LLM_TYPE: '{self.llm_type}'. Accepted values: 'openai', 'ollama'."
            )
        if self.embedder_type not in {"openai", "local"}:
            raise ValueError(
                f"Invalid EMBEDDER_TYPE: '{self.embedder_type}'. Accepted values: 'openai', 'local'."
            )
        # OpenAI key is required only if either component uses the cloud
        needs_openai = self.llm_type == "openai" or self.embedder_type == "openai"
        if needs_openai and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY missing. Required when LLM_TYPE=openai or EMBEDDER_TYPE=openai.\n"
                "For a 100% local free mode: LLM_TYPE=ollama + EMBEDDER_TYPE=local"
            )


# Global instance — imported everywhere in the application
settings = Settings()
