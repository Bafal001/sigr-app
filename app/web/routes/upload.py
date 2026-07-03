"""
Routes API — Upload de fichiers et gestion des rapports.
"""

from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.models.schemas import (
    APIResponse,
    FileDetail,
    ReportInReview,
    UploadResponse,
)
from app.core.services import report_service

router = APIRouter(prefix="/api", tags=["Rapports"])

# Types MIME autorisés pour l'upload
ALLOWED_MIME_TYPES: set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
    "text/plain",
}


# ---------------------------------------------------------------------------
# POST /api/upload
# ---------------------------------------------------------------------------
@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Uploader un fichier de rapport",
    description=(
        "Accepte un fichier (PDF, DOCX, XLSX, CSV) et le sauvegarde. "
        "Retourne un file_id unique et le nombre de lignes/rapports détectés."
    ),
)
async def upload_file(
    file: UploadFile = File(..., description="Fichier de rapport à uploader"),
) -> UploadResponse:
    """
    Endpoint d'upload de fichier.
    - Valide le type MIME
    - Sauvegarde le fichier dans uploads/
    - Compte le nombre de lignes (pour les Excel/CSV)
    - Retourne les métadonnées
    """
    # Validation MIME (optionnelle mais recommandée)
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Type MIME non supporté : '{file.content_type}'. "
                f"Types acceptés : PDF, DOCX, XLSX, CSV, TXT."
            ),
        )

    # Lecture du contenu
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la lecture du fichier : {str(e)}",
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est vide.",
        )

    # Délégation au service métier
    try:
        result = report_service.save_uploaded_file(
            original_filename=file.filename or "unknown",
            file_content=content,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne lors du traitement : {str(e)}",
        )


# ---------------------------------------------------------------------------
# GET /api/reports/{file_id}
# ---------------------------------------------------------------------------
@router.get(
    "/reports/{file_id}",
    response_model=FileDetail,
    summary="Détail d'un fichier uploadé",
    description="Récupère les informations et rapports extraits d'un fichier.",
)
async def get_file_reports(file_id: str) -> FileDetail:
    """
    Retourne les détails et la liste des rapports extraits
    pour un fichier donné (identifié par son file_id).
    """
    detail = report_service.get_file_detail(file_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fichier avec l'ID '{file_id}' introuvable.",
        )
    return detail


# ---------------------------------------------------------------------------
# GET /api/reports
# ---------------------------------------------------------------------------
@router.get(
    "/reports",
    response_model=list[FileDetail],
    summary="Liste tous les fichiers uploadés",
    description="Retourne la liste de tous les fichiers uploadés avec leurs statuts.",
)
async def list_reports() -> list[FileDetail]:
    """Liste tous les fichiers uploadés."""
    return report_service.list_uploaded_files()


# ---------------------------------------------------------------------------
# DELETE /api/reports/{file_id}
# ---------------------------------------------------------------------------
@router.delete(
    "/reports/{file_id}",
    response_model=APIResponse,
    summary="Supprimer un fichier uploadé",
)
async def delete_report(file_id: str) -> APIResponse:
    """Supprime un fichier uploadé par son ID."""
    deleted = report_service.delete_uploaded_file(file_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fichier avec l'ID '{file_id}' introuvable.",
        )
    return APIResponse(
        success=True,
        message=f"Fichier '{file_id}' supprimé avec succès.",
    )
