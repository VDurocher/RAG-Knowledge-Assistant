"""Configuration centralisée — chargée depuis les variables d'environnement."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Paramètres de l'application chargés depuis .env."""

    # Embeddings : "openai" (payant, meilleure qualité) ou "local" (HuggingFace, gratuit)
    embedder_type: str = field(
        default_factory=lambda: os.getenv("EMBEDDER_TYPE", "local")
    )

    # Moteur de génération : "openai" (cloud) ou "ollama" (local, gratuit)
    llm_type: str = field(
        default_factory=lambda: os.getenv("LLM_TYPE", "openai")
    )

    # Clé API OpenAI — requise uniquement si llm_type="openai" (ou embedder_type="openai")
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )

    # Modèle de génération OpenAI
    openai_chat_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    )

    # Configuration Ollama (mode local entièrement gratuit)
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2")
    )

    # Modèle HuggingFace pour les embeddings locaux
    local_embed_model: str = field(
        default_factory=lambda: os.getenv(
            "LOCAL_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
    )

    # Paramètres de découpage du texte
    chunk_size: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_SIZE", "1000"))
    )
    chunk_overlap: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "200"))
    )

    # Nombre de documents récupérés par requête
    retrieval_k: int = field(
        default_factory=lambda: int(os.getenv("RETRIEVAL_K", "4"))
    )

    # Seuil de confiance minimum (0.0 = désactivé) — filtre les docs non pertinents
    retrieval_score_threshold: float = field(
        default_factory=lambda: float(os.getenv("RETRIEVAL_SCORE_THRESHOLD", "0.3"))
    )

    # Recherche hybride BM25 + sémantique (nécessite rank-bm25)
    hybrid_search: bool = field(
        default_factory=lambda: os.getenv("HYBRID_SEARCH", "false").lower() == "true"
    )

    # Poids BM25 dans la recherche hybride (0.4 = 40% lexical, 60% sémantique)
    bm25_weight: float = field(
        default_factory=lambda: float(os.getenv("BM25_WEIGHT", "0.4"))
    )

    # Chemins des dossiers
    knowledge_base_path: Path = field(default_factory=lambda: Path("knowledge_base"))
    vector_store_path: Path = field(default_factory=lambda: Path("vector_store"))

    def validate(self) -> None:
        """Vérifie que la configuration est valide avant le démarrage."""
        if self.llm_type not in {"openai", "ollama"}:
            raise ValueError(
                f"LLM_TYPE invalide: '{self.llm_type}'. Valeurs acceptées: 'openai', 'ollama'."
            )
        if self.embedder_type not in {"openai", "local"}:
            raise ValueError(
                f"EMBEDDER_TYPE invalide: '{self.embedder_type}'. Valeurs acceptées: 'openai', 'local'."
            )
        # La clé OpenAI est requise seulement si l'un des deux composants utilise le cloud
        needs_openai = self.llm_type == "openai" or self.embedder_type == "openai"
        if needs_openai and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY manquant. Requis quand LLM_TYPE=openai ou EMBEDDER_TYPE=openai.\n"
                "Pour un mode 100% local et gratuit : LLM_TYPE=ollama + EMBEDDER_TYPE=local"
            )


# Instance globale — importée partout dans l'application
settings = Settings()
