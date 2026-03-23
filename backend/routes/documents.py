"""Routes /api/documents — liste, upload, suppression + rebuild index."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from backend.deps import get_state, reload_pipeline
from core.config import settings
from core.loader import list_source_files

router = APIRouter()

# Extensions acceptées à l'upload
_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".docx", ".json"}


class DocumentInfo(BaseModel):
    """Métadonnées d'un fichier de la knowledge base."""

    name: str
    extension: str


class StatusResponse(BaseModel):
    """État du pipeline retourné par /api/status."""

    doc_count: int
    llm_label: str
    embedder_label: str


@router.get("/documents", response_model=list[DocumentInfo])
def list_documents() -> list[DocumentInfo]:
    """Retourne la liste des documents indexés."""
    files = list_source_files(settings.knowledge_base_path)
    return [DocumentInfo(name=f, extension=Path(f).suffix.lower()) for f in files]


@router.post("/documents/upload", response_model=list[DocumentInfo])
async def upload_documents(files: list[UploadFile]) -> list[DocumentInfo]:
    """Upload un ou plusieurs fichiers dans knowledge_base et recharge le pipeline."""
    saved: list[DocumentInfo] = []

    for file in files:
        if not file.filename:
            continue

        ext = Path(file.filename).suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Format non supporté : {ext}. Formats acceptés : {', '.join(_ALLOWED_EXTENSIONS)}",
            )

        dest = settings.knowledge_base_path / file.filename
        dest.write_bytes(await file.read())
        saved.append(DocumentInfo(name=file.filename, extension=ext))

    if saved:
        reload_pipeline()

    return saved


@router.delete("/documents/{filename}")
def delete_document(filename: str) -> dict[str, str]:
    """Supprime un fichier de knowledge_base et recharge le pipeline."""
    # Sécurité : empêcher les path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Nom de fichier invalide.")

    target = settings.knowledge_base_path / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Fichier introuvable : {filename}")

    target.unlink()
    reload_pipeline()

    return {"deleted": filename}


@router.post("/rebuild")
def rebuild_index() -> dict[str, str]:
    """Force un rebuild complet de l'index FAISS."""
    reload_pipeline(force_rebuild=True)
    state = get_state()
    return {"status": "ok", "doc_count": str(state.doc_count)}


@router.get("/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    """Retourne l'état courant du pipeline."""
    state = get_state()
    return StatusResponse(
        doc_count=state.doc_count,
        llm_label=state.llm_label,
        embedder_label=state.embedder_label,
    )
