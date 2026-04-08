"""Routes /api/documents — list, upload, delete + rebuild index."""

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

# Accepted upload extensions
_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".docx", ".json"}

# Maximum allowed file size per upload: 10 MB
_MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024


class DocumentInfo(BaseModel):
    """Metadata for a file in the knowledge base."""

    name: str
    extension: str


class StatusResponse(BaseModel):
    """Pipeline state returned by /api/status."""

    doc_count: int
    llm_label: str
    embedder_label: str


@router.get("/documents", response_model=list[DocumentInfo], dependencies=[Depends(require_api_key)])
def list_documents() -> list[DocumentInfo]:
    """Returns the list of indexed documents."""
    files = list_source_files(settings.knowledge_base_path)
    return [DocumentInfo(name=f, extension=Path(f).suffix.lower()) for f in files]


@router.post("/documents/upload", response_model=list[DocumentInfo], dependencies=[Depends(require_api_key)])
async def upload_documents(files: list[UploadFile]) -> list[DocumentInfo]:
    """Uploads one or more files into knowledge_base and reloads the pipeline."""
    saved: list[DocumentInfo] = []

    for file in files:
        if not file.filename:
            continue

        # Sanitise filename to remove any path traversal
        safe_name = secure_filename(os.path.basename(file.filename))
        if not safe_name:
            raise HTTPException(status_code=400, detail="Invalid filename.")

        ext = Path(safe_name).suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {ext}. Accepted formats: {', '.join(_ALLOWED_EXTENSIONS)}",
            )

        # Read content and verify size
        content = await file.read()
        if len(content) > _MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {safe_name}. Limit: 10 MB.",
            )

        dest = settings.knowledge_base_path / safe_name
        # Verify the final path stays within the allowed folder
        if not os.path.realpath(dest).startswith(
            os.path.realpath(settings.knowledge_base_path)
        ):
            raise HTTPException(status_code=400, detail="Invalid destination path.")

        dest.write_bytes(content)
        saved.append(DocumentInfo(name=safe_name, extension=ext))

    if saved:
        reload_pipeline()

    return saved


@router.delete("/documents/{filename}", dependencies=[Depends(require_api_key)])
def delete_document(filename: str) -> dict[str, str]:
    """Deletes a file from knowledge_base and reloads the pipeline."""
    # Sanitise filename to remove any path traversal
    safe_name = secure_filename(os.path.basename(filename))
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    target = settings.knowledge_base_path / safe_name
    # Verify the final path stays within the allowed folder
    if not os.path.realpath(target).startswith(
        os.path.realpath(settings.knowledge_base_path)
    ):
        raise HTTPException(status_code=400, detail="Invalid destination path.")

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {safe_name}")

    target.unlink()
    reload_pipeline()

    return {"deleted": safe_name}


@router.post("/rebuild", dependencies=[Depends(require_api_key)])
def rebuild_index() -> dict[str, str]:
    """Forces a full rebuild of the FAISS index."""
    reload_pipeline(force_rebuild=True)
    state = get_state()
    return {"status": "ok", "doc_count": str(state.doc_count)}


@router.get("/status", response_model=StatusResponse, dependencies=[Depends(require_api_key)])
def get_status() -> StatusResponse:
    """Returns the current pipeline state."""
    state = get_state()
    return StatusResponse(
        doc_count=state.doc_count,
        llm_label=state.llm_label,
        embedder_label=state.embedder_label,
    )
