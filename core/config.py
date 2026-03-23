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

    # Clé API OpenAI — requise pour la génération (et les embeddings si embedder_type="openai")
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )

    # Modèle de génération OpenAI
    openai_chat_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
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

    # Chemins des dossiers
    knowledge_base_path: Path = field(default_factory=lambda: Path("knowledge_base"))
    vector_store_path: Path = field(default_factory=lambda: Path("vector_store"))

    def validate(self) -> None:
        """Vérifie que la configuration est valide avant le démarrage."""
        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY manquant. Créez un fichier .env à partir de .env.example."
            )
        if self.embedder_type not in {"openai", "local"}:
            raise ValueError(
                f"EMBEDDER_TYPE invalide: '{self.embedder_type}'. Valeurs acceptées: 'openai', 'local'."
            )


# Instance globale — importée partout dans l'application
settings = Settings()
