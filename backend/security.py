"""Authentification par API Key — protège toutes les routes FastAPI."""

import os

from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

# En-tête HTTP attendu pour l'authentification
_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)


def require_api_key(api_key: str = Security(_API_KEY_HEADER)) -> None:
    """
    Vérifie que l'en-tête X-API-Key correspond à la valeur configurée via API_KEY.

    Lève une erreur 403 si la clé est absente, invalide ou si API_KEY n'est pas défini.
    """
    expected_key = os.getenv("API_KEY", "")

    # Refus explicite si la variable d'environnement n'est pas configurée
    if not expected_key:
        raise HTTPException(
            status_code=500,
            detail="API_KEY non configurée côté serveur. Définissez la variable d'environnement API_KEY.",
        )

    if api_key != expected_key:
        raise HTTPException(
            status_code=403,
            detail="Clé API invalide ou absente.",
        )
