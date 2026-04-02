"""Routes /api/documents — liste, upload, suppression + rebuild index."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from werkzeug.utils import secure_filename

from backend.deps import get_state, reload_pipeline
from backend.security import require_api_key
from core.config import settings
from core.loader import list_source_files

router = APIRouter()

# Extensions acceptées à l'upload
_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".docx", ".json"}

# Taille maximale autorisée par fichier uploadé : 10 Mo
_MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024


class DocumentInfo(BaseModel):
    """Métadonnées d'un fichier de la knowledge base."""

    name: str
    extension: str


class StatusResponse(BaseModel):
    """État du pipeline retourné par /api/status."""

    doc_count: int
    llm_label: str
    embedder_label: str


@router.get("/documents", response_model=list[DocumentInfo], dependencies=[Depends(require_api_key)])
def list_documents() -> list[DocumentInfo]:
    """Retourne la liste des documents indexés."""
    files = list_source_files(settings.knowledge_base_path)
    return [DocumentInfo(name=f, extension=Path(f).suffix.lower()) for f in files]


@router.post("/documents/upload", response_model=list[DocumentInfo], dependencies=[Depends(require_api_key)])
async def upload_documents(files: list[UploadFile]) -> list[DocumentInfo]:
    """Upload un ou plusieurs fichiers dans knowledge_base et recharge le pipeline."""
    saved: list[DocumentInfo] = []

    for file in files:
        if not file.filename:
            continue

        # Nettoyage du nom de fichier pour éliminer tout path traversal
        safe_name = secure_filename(os.path.basename(file.filename))
        if not safe_name:
            raise HTTPException(status_code=400, detail="Nom de fichier invalide.")

        ext = Path(safe_name).suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Format non supporté : {ext}. Formats acceptés : {', '.join(_ALLOWED_EXTENSIONS)}",
            )

        # Lecture du contenu et vérification de la taille
        content = await file.read()
        if len(content) > _MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Fichier trop volumineux : {safe_name}. Limite : 10 Mo.",
            )

        dest = settings.knowledge_base_path / safe_name
        # Vérification que le chemin final reste dans le dossier autorisé
        if not os.path.realpath(dest).startswith(
            os.path.realpath(settings.knowledge_base_path)
        ):
            raise HTTPException(status_code=400, detail="Chemin de destination invalide.")

        dest.write_bytes(content)
        saved.append(DocumentInfo(name=safe_name, extension=ext))

    if saved:
        reload_pipeline()

    return saved


@router.delete("/documents/{filename}", dependencies=[Depends(require_api_key)])
def delete_document(filename: str) -> dict[str, str]:
    """Supprime un fichier de knowledge_base et recharge le pipeline."""
    # Nettoyage du nom de fichier pour éliminer tout path traversal
    safe_name = secure_filename(os.path.basename(filename))
    if not safe_name:
        raise HTTPException(status_code=400, detail="Nom de fichier invalide.")

    target = settings.knowledge_base_path / safe_name
    # Vérification que le chemin final reste dans le dossier autorisé
    if not os.path.realpath(target).startswith(
        os.path.realpath(settings.knowledge_base_path)
    ):
        raise HTTPException(status_code=400, detail="Chemin de destination invalide.")

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Fichier introuvable : {safe_name}")

    target.unlink()
    reload_pipeline()

    return {"deleted": safe_name}


@router.post("/rebuild", dependencies=[Depends(require_api_key)])
def rebuild_index() -> dict[str, str]:
    """Force un rebuild complet de l'index FAISS."""
    reload_pipeline(force_rebuild=True)
    state = get_state()
    return {"status": "ok", "doc_count": str(state.doc_count)}


@router.get("/status", response_model=StatusResponse, dependencies=[Depends(require_api_key)])
def get_status() -> StatusResponse:
    """Retourne l'état courant du pipeline."""
    state = get_state()
    return StatusResponse(
        doc_count=state.doc_count,
        llm_label=state.llm_label,
        embedder_label=state.embedder_label,
    )
