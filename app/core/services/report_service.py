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


def extract_and_get_reports(file_id: str) -> Optional[FileDetail]:
    """
    Déclenche l'extraction IA pour un fichier uploadé et retourne
    les rapports extraits.

    - PDF/Word : extraction texte → LLM → JSON structuré
    - Excel/CSV : lecture directe sans LLM

    Args:
        file_id: Identifiant du fichier.

    Returns:
        FileDetail enrichi avec les rapports extraits, ou None si introuvable.
    """
    detail = get_file_detail(file_id)
    if detail is None:
        return None

    # Trouver le chemin physique du fichier
    upload_dir = _ensure_upload_dir()
    found_path: Optional[Path] = None
    for f in upload_dir.iterdir():
        if f.is_file() and f.stem == file_id:
            found_path = f
            break

    if found_path is None:
        return None

    # Déléguer à l'AI extraction service
    from app.core.services.ai_extraction_service import extract_reports_from_file

    reports = extract_reports_from_file(found_path, detail.file_type)
    detail.reports = reports
    detail.status = "extracted"

    return detail


def save_report_to_db(report_data: dict) -> int:
    """
    Sauvegarde un rapport structuré dans la base SQLite.
    Utilise le Mapper pour transformer les données brutes.

    Args:
        report_data: Données structurées du rapport (JSON LLM ou ligne Excel mappée).

    Returns:
        ID du rapport créé dans la base.

    Raises:
        ValueError: Si les données sont invalides.
    """
    from app.core.services.mapper import (
        map_llm_json_to_db,
        map_excel_row_to_db,
    )

    # Déterminer la source (LLM ou Excel) et mapper
    # Si les données ont déjà les sections SIGR, c'est du LLM
    if "metadata" in report_data and "activite_pastorale" in report_data:
        mapped = map_llm_json_to_db(report_data)
    else:
        mapped = map_excel_row_to_db(report_data)

    # Insérer dans la base
    rapport_id = _insert_rapport(mapped)
    return rapport_id


def _insert_rapport(data: dict) -> int:
    """
    Insère un rapport complet (toutes sections) dans SQLite.
    Retourne l'ID du rapport créé.
    """
    from app.core.models.models import (
        ActiviteDOS,
        ActiviteJeunesse,
        ActiviteMusique,
        ActivitePastorale,
        ActiviteProphetique,
        Commentaire,
        Conclusion,
        Coordination,
        DirigeantMusical,
        EncadreurJeunesse,
        Formation,
        InventaireIntendance,
        Mariage,
        MedecineHomme,
        Paroisse,
        PatrimoineImmobilier,
        Rapport,
        Signataire,
    )
    from app.infrastructure.database.session import SessionLocal

    db = SessionLocal()
    try:
        metadata = data.get("metadata", {})

        # 1. Coordination (créer ou récupérer)
        coord_name = metadata.get("coordination_nom")
        if coord_name:
            coordination = (
                db.query(Coordination).filter(Coordination.nom == coord_name).first()
            )
            if coordination is None:
                coordination = Coordination(
                    nom=coord_name,
                    adresse=metadata.get("coordination_adresse"),
                    email=metadata.get("coordination_email"),
                    telephone=metadata.get("coordination_telephone"),
                )
                db.add(coordination)
                db.flush()
        else:
            coordination = Coordination(nom="Inconnue")
            db.add(coordination)
            db.flush()

        # 2. Rapport
        annee = metadata.get("annee") or datetime.utcnow().year
        trimestre = metadata.get("trimestre") or 1
        rapport = Rapport(
            coordination_id=coordination.id,
            annee=int(annee) if annee else datetime.utcnow().year,
            trimestre=int(trimestre) if trimestre else 1,
            statut="valide",
            date_soumission=datetime.utcnow(),
        )
        db.add(rapport)
        db.flush()

        # 3. Paroisses
        for p in data.get("paroisses", []):
            if p.get("nom"):
                db.add(Paroisse(rapport_id=rapport.id, **p))

        # 4. Activités (one-to-one)
        for model_class, section_key in [
            (ActivitePastorale, "activite_pastorale"),
            (ActiviteProphetique, "activite_prophetique"),
            (MedecineHomme, "medecine_homme"),
            (ActiviteDOS, "activite_dos"),
            (ActiviteMusique, "activite_musique"),
            (ActiviteJeunesse, "activite_jeunesse"),
            (InventaireIntendance, "inventaire_intendance"),
        ]:
            section_data = data.get(section_key, {})
            if section_data:
                # Filtrer uniquement les colonnes qui existent dans le modèle
                valid_cols = {
                    c.name
                    for c in model_class.__table__.columns
                    if c.name not in ("id", "rapport_id")
                }
                filtered = {k: v for k, v in section_data.items() if k in valid_cols}
                if filtered:
                    db.add(model_class(rapport_id=rapport.id, **filtered))

        # 5. Mariages
        for m in data.get("mariages", []):
            if m.get("epoux_nom") or m.get("epouse_nom"):
                db.add(Mariage(rapport_id=rapport.id, **m))

        # 6. Formations
        for f in data.get("formations", []):
            if f.get("type"):
                db.add(Formation(rapport_id=rapport.id, **f))

        # 7. Patrimoine
        for p in data.get("patrimoine_immobilier", []):
            if p.get("localisation") or p.get("paroisse"):
                db.add(PatrimoineImmobilier(rapport_id=rapport.id, **p))

        # 8. Dirigeants musicaux
        for d in data.get("dirigeants_musicaux", []):
            if d.get("nom"):
                db.add(DirigeantMusical(rapport_id=rapport.id, **d))

        # 9. Encadreurs jeunesse
        for e in data.get("encadreurs_jeunesse", []):
            if e.get("nom"):
                db.add(EncadreurJeunesse(rapport_id=rapport.id, **e))

        # 10. Commentaires
        commentaires = data.get("commentaires", {})
        for section, texte in commentaires.items():
            if texte:
                db.add(
                    Commentaire(
                        rapport_id=rapport.id, section=section, texte=str(texte)
                    )
                )

        # 11. Conclusion
        conclusion_text = data.get("conclusion")
        if conclusion_text:
            db.add(Conclusion(rapport_id=rapport.id, texte=str(conclusion_text)))

        # 12. Signataires
        signataires = data.get("signataires", {})
        for role, nom in signataires.items():
            if nom:
                db.add(Signataire(rapport_id=rapport.id, role=role, nom=str(nom)))

        db.commit()
        return rapport.id

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
