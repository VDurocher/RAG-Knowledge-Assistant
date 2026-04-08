"""API Key authentication — protects all FastAPI routes."""

import os

from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

# Expected HTTP header for authentication
_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)


def require_api_key(api_key: str = Security(_API_KEY_HEADER)) -> None:
    """
    Verifies that the X-API-Key header matches the value configured via API_KEY.

    Raises a 403 error if the key is missing, invalid, or if API_KEY is not set.
    """
    expected_key = os.getenv("API_KEY", "")

    # Explicit rejection if the environment variable is not configured
    if not expected_key:
        raise HTTPException(
            status_code=500,
            detail="API_KEY not configured on the server. Set the API_KEY environment variable.",
        )

    if api_key != expected_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key.",
        )
