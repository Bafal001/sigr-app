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
# POST /api/reports/{file_id}/extract
# ---------------------------------------------------------------------------
@router.post(
    "/reports/{file_id}/extract",
    response_model=FileDetail,
    summary="Extraire les données d'un fichier via IA",
    description=(
        "Déclenche l'extraction intelligente :\n"
        "- PDF/Word : OCR + LLM DeepSeek → JSON structuré\n"
        "- Excel/CSV : lecture directe sans LLM"
    ),
)
async def extract_file_data(file_id: str) -> FileDetail:
    """
    Lance l'extraction des données d'un fichier uploadé.
    """
    detail = report_service.extract_and_get_reports(file_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fichier avec l'ID '{file_id}' introuvable.",
        )
    return detail


# ---------------------------------------------------------------------------
# POST /api/reports/{file_id}/save
# ---------------------------------------------------------------------------
@router.post(
    "/reports/{file_id}/save",
    response_model=APIResponse,
    summary="Sauvegarder les rapports en base de données",
    description="Valide et enregistre les rapports extraits dans SQLite.",
)
async def save_reports(file_id: str) -> APIResponse:
    """
    Sauvegarde les rapports extraits d'un fichier dans la base SQLite.
    """
    detail = report_service.extract_and_get_reports(file_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fichier avec l'ID '{file_id}' introuvable.",
        )

    saved_ids: list[int] = []
    errors: list[str] = []

    for report in detail.reports:
        if not report.raw_data:
            continue
        try:
            rid = report_service.save_report_to_db(report.raw_data)
            saved_ids.append(rid)
        except Exception as e:
            errors.append(f"Ligne {report.row_index}: {str(e)}")

    return APIResponse(
        success=len(errors) == 0,
        message=f"{len(saved_ids)} rapports sauvegardés."
        + (f" {len(errors)} erreurs." if errors else ""),
        data={"saved_ids": saved_ids, "errors": errors},
    )


# ---------------------------------------------------------------------------
# GET /api/reports/db/{rapport_id}/export
# ---------------------------------------------------------------------------
@router.get(
    "/reports/db/{rapport_id}/export",
    summary="Exporter un rapport en Excel",
    description="Génère un fichier .xlsx conforme au modèle à partir des données SQLite.",
)
async def export_rapport(rapport_id: int):
    """
    Exporte un rapport depuis SQLite vers un fichier Excel.
    """
    from fastapi.responses import FileResponse

    from app.core.services.excel_export_service import export_rapport_to_excel

    try:
        output_path = export_rapport_to_excel(rapport_id)
        return FileResponse(
            path=str(output_path),
            filename=f"rapport_{rapport_id}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


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
