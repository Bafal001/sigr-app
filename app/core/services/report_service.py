"""
Service de gestion des rapports — Upload, analyse, extraction.
Respecte Clean Architecture : logique métier pure, sans dépendances web.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from app.core.models.schemas import FileDetail, ReportInReview, UploadResponse

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"

# Types de fichiers supportés
ALLOWED_EXTENSIONS: set[str] = {
    ".pdf",
    ".docx",
    ".doc",
    ".xlsx",
    ".xls",
    ".csv",
    ".txt",
}

# Mapping extension → type lisible
EXTENSION_TYPE_MAP: dict[str, str] = {
    ".pdf": "pdf",
    ".docx": "word",
    ".doc": "word",
    ".xlsx": "excel",
    ".xls": "excel",
    ".csv": "csv",
    ".txt": "text",
}


# ---------------------------------------------------------------------------
# Fonctions du service
# ---------------------------------------------------------------------------
def _ensure_upload_dir() -> Path:
    """Crée le dossier uploads/ s'il n'existe pas."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def _get_file_type(filename: str) -> str:
    """Détermine le type de fichier à partir de son extension."""
    ext = Path(filename).suffix.lower()
    return EXTENSION_TYPE_MAP.get(ext, "unknown")


def _is_allowed_extension(filename: str) -> bool:
    """Vérifie si l'extension du fichier est autorisée."""
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def _count_rows(file_path: Path, file_type: str) -> int:
    """
    Compte le nombre de lignes/rapports détectés dans le fichier.
    - Pour Excel/CSV : compte les lignes de données (hors en-tête)
    - Pour PDF/Word : retourne 1 (un seul rapport par fichier)
    """
    if file_type in ("excel", "csv"):
        try:
            import pandas as pd

            if file_type == "csv":
                df = pd.read_csv(file_path)
            else:
                # Pour Excel, on lit le premier onglet
                df = pd.read_excel(file_path, sheet_name=0)

            # Les données commencent après la ligne d'en-tête (row 0)
            # On vérifie que la première ligne n'est pas un header
            # Dans notre modèle Excel, les données commencent à la ligne 1 (index 1)
            # On retourne le nombre de lignes avec au moins une valeur non-NaN
            data_rows = df.dropna(how="all").shape[0]
            # On soustrait 1 pour la ligne d'en-tête si elle existe
            if data_rows > 0:
                # Pour Excel: ligne 0 = headers, lignes 1+ = données
                return max(0, len(df) - 1)
            return 0
        except ImportError:
            return 1
        except Exception:
            return 1
    else:
        # PDF, Word : un rapport par fichier
        return 1


def save_uploaded_file(
    original_filename: str,
    file_content: bytes,
) -> UploadResponse:
    """
    Sauvegarde le fichier uploadé et retourne les métadonnées.

    Args:
        original_filename: Nom original du fichier.
        file_content: Contenu binaire du fichier.

    Returns:
        UploadResponse avec file_id, type, nombre de lignes.

    Raises:
        ValueError: Si le type de fichier n'est pas supporté.
    """
    # Validation de l'extension
    if not _is_allowed_extension(original_filename):
        raise ValueError(
            f"Type de fichier non supporté : '{Path(original_filename).suffix}'. "
            f"Extensions autorisées : {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Création du dossier
    upload_dir = _ensure_upload_dir()

    # Génération d'un ID unique
    file_id = str(uuid4())
    file_type = _get_file_type(original_filename)
    ext = Path(original_filename).suffix

    # Sauvegarde physique du fichier
    saved_filename = f"{file_id}{ext}"
    saved_path = upload_dir / saved_filename

    with open(saved_path, "wb") as f:
        f.write(file_content)

    # Comptage des lignes
    rows_detected = _count_rows(saved_path, file_type)

    return UploadResponse(
        status="received",
        file_id=file_id,
        original_filename=original_filename,
        file_type=file_type,
        rows_detected=rows_detected,
        uploaded_at=datetime.utcnow(),
    )


def get_file_detail(file_id: str) -> Optional[FileDetail]:
    """
    Récupère les informations détaillées d'un fichier uploadé.

    Args:
        file_id: Identifiant du fichier (UUID sans extension).

    Returns:
        FileDetail ou None si le fichier n'existe pas.
    """
    upload_dir = _ensure_upload_dir()

    # Recherche du fichier par son ID (toutes extensions)
    found_path: Optional[Path] = None
    for f in upload_dir.iterdir():
        if f.is_file() and f.stem == file_id:
            found_path = f
            break

    if found_path is None:
        return None

    file_type = _get_file_type(found_path.name)
    rows = _count_rows(found_path, file_type)
    stat = found_path.stat()

    return FileDetail(
        file_id=file_id,
        original_filename=found_path.name,
        file_type=file_type,
        rows_detected=rows,
        uploaded_at=datetime.fromtimestamp(stat.st_ctime),
        reports=[],
        status="pending_validation",
    )


def list_uploaded_files() -> list[FileDetail]:
    """
    Liste tous les fichiers uploadés avec leurs détails.
    """
    upload_dir = _ensure_upload_dir()
    files: list[FileDetail] = []

    for f in sorted(
        upload_dir.iterdir(), key=lambda x: x.stat().st_ctime, reverse=True
    ):
        if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS:
            detail = get_file_detail(f.stem)
            if detail is not None:
                files.append(detail)

    return files


def delete_uploaded_file(file_id: str) -> bool:
    """
    Supprime un fichier uploadé.

    Returns:
        True si supprimé, False si non trouvé.
    """
    upload_dir = _ensure_upload_dir()

    for f in upload_dir.iterdir():
        if f.is_file() and f.stem == file_id:
            f.unlink()
            return True

    return False
