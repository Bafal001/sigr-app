"""
Service d'export Excel — Génère un fichier .xlsx conforme au modèle
à partir des données stockées dans SQLite.

Utilise pandas + openpyxl pour préserver la structure du modèle.
"""

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from app.infrastructure.database.session import SessionLocal

# Chemin vers le modèle Excel
_MODEL_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "Rapports_1_Trimestre_20262026-07-03_06_54_42.xlsx"
)


def export_rapport_to_excel(
    rapport_id: int, output_path: Optional[Path] = None
) -> Path:
    """
    Exporte un rapport depuis SQLite vers un fichier Excel conforme au modèle.

    Args:
        rapport_id: ID du rapport dans la base de données.
        output_path: Chemin de sortie (optionnel). Si None, un fichier temporaire est créé.

    Returns:
        Chemin vers le fichier Excel généré.

    Raises:
        ValueError: Si le rapport n'existe pas.
    """
    db = SessionLocal()
    try:
        # 1. Charger le rapport depuis la base
        rapport_data = _load_rapport_from_db(db, rapport_id)

        if rapport_data is None:
            raise ValueError(f"Rapport avec l'ID {rapport_id} introuvable.")

        # 2. Charger le modèle Excel
        if not _MODEL_PATH.exists():
            # Si le modèle n'existe pas, créer un Excel simple
            return _export_simple_excel(rapport_data, output_path)

        template_df = pd.read_excel(_MODEL_PATH, sheet_name=0, header=None)

        # 3. Peupler les cellules avec les données du rapport
        populated_df = _populate_template(template_df, rapport_data)

        # 4. Sauvegarder
        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=".xlsx"))

        populated_df.to_excel(output_path, index=False, header=False, engine="openpyxl")

        return output_path

    finally:
        db.close()


def _load_rapport_from_db(db, rapport_id: int) -> Optional[dict]:
    """
    Charge toutes les données d'un rapport depuis SQLite.
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
        ServiteurRH,
        Signataire,
    )

    rapport = db.query(Rapport).filter(Rapport.id == rapport_id).first()
    if rapport is None:
        return None

    coordination = (
        db.query(Coordination)
        .filter(Coordination.id == rapport.coordination_id)
        .first()
    )

    paroisses = db.query(Paroisse).filter(Paroisse.rapport_id == rapport_id).all()
    activite_past = (
        db.query(ActivitePastorale)
        .filter(ActivitePastorale.rapport_id == rapport_id)
        .first()
    )
    activite_proph = (
        db.query(ActiviteProphetique)
        .filter(ActiviteProphetique.rapport_id == rapport_id)
        .first()
    )
    medecine = (
        db.query(MedecineHomme).filter(MedecineHomme.rapport_id == rapport_id).first()
    )
    mariages = db.query(Mariage).filter(Mariage.rapport_id == rapport_id).all()
    formations = db.query(Formation).filter(Formation.rapport_id == rapport_id).all()
    inventaire = (
        db.query(InventaireIntendance)
        .filter(InventaireIntendance.rapport_id == rapport_id)
        .first()
    )
    patrimoines = (
        db.query(PatrimoineImmobilier)
        .filter(PatrimoineImmobilier.rapport_id == rapport_id)
        .all()
    )
    dos = db.query(ActiviteDOS).filter(ActiviteDOS.rapport_id == rapport_id).first()
    musique = (
        db.query(ActiviteMusique)
        .filter(ActiviteMusique.rapport_id == rapport_id)
        .first()
    )
    dirigeants = (
        db.query(DirigeantMusical)
        .filter(DirigeantMusical.rapport_id == rapport_id)
        .all()
    )
    jeunesse = (
        db.query(ActiviteJeunesse)
        .filter(ActiviteJeunesse.rapport_id == rapport_id)
        .first()
    )
    encadreurs = (
        db.query(EncadreurJeunesse)
        .filter(EncadreurJeunesse.rapport_id == rapport_id)
        .all()
    )
    serviteurs = (
        db.query(ServiteurRH).filter(ServiteurRH.rapport_id == rapport_id).all()
    )
    commentaires = (
        db.query(Commentaire).filter(Commentaire.rapport_id == rapport_id).all()
    )
    conclusion = (
        db.query(Conclusion).filter(Conclusion.rapport_id == rapport_id).first()
    )
    signataires = db.query(Signataire).filter(Signataire.rapport_id == rapport_id).all()

    return {
        "metadata": {
            "coordination_nom": coordination.nom if coordination else None,
            "annee": rapport.annee,
            "trimestre": rapport.trimestre,
            "coordination_adresse": coordination.adresse if coordination else None,
            "coordination_email": coordination.email if coordination else None,
            "coordination_telephone": coordination.telephone if coordination else None,
        },
        "paroisses": [
            {
                "nom": p.nom,
                "adresse": p.adresse,
                "entite": p.entite,
                "nature_parcelle": p.nature_parcelle,
            }
            for p in paroisses
        ],
        "activite_pastorale": _model_to_dict(activite_past),
        "activite_prophetique": _model_to_dict(activite_proph),
        "medecine_homme": _model_to_dict(medecine),
        "mariages": [
            {
                "date": str(m.date) if m.date else None,
                "epoux_nom": m.epoux_nom,
                "epouse_nom": m.epouse_nom,
                "paroisse": m.paroisse,
                "observation": m.observation,
            }
            for m in mariages
        ],
        "formations": [
            {
                "type": f.type,
                "date": str(f.date) if f.date else None,
                "theme": f.theme,
                "formateur": f.formateur,
                "observation": f.observation,
            }
            for f in formations
        ],
        "inventaire_intendance": _model_to_dict(inventaire),
        "patrimoine_immobilier": [
            {
                "entite": p.entite,
                "paroisse": p.paroisse,
                "localisation": p.localisation,
                "superficie": p.superficie,
                "mise_en_valeur": p.mise_en_valeur,
                "observation": p.observation,
            }
            for p in patrimoines
        ],
        "activite_dos": _model_to_dict(dos),
        "activite_musique": _model_to_dict(musique),
        "dirigeants_musicaux": [
            {
                "nom": d.nom,
                "paroisse": d.paroisse,
                "echelon": d.echelon,
                "fonction": d.fonction,
                "onction": d.onction,
                "likabo": d.likabo,
                "statut": d.statut,
                "naissance": str(d.naissance) if d.naissance else None,
                "etat_civil": d.etat_civil,
                "contact": d.contact,
            }
            for d in dirigeants
        ],
        "activite_jeunesse": _model_to_dict(jeunesse),
        "encadreurs_jeunesse": [
            {
                "nom": e.nom,
                "paroisse": e.paroisse,
                "echelon": e.echelon,
                "fonction": e.fonction,
                "onction": e.onction,
                "likabo": e.likabo,
                "statut": e.statut,
                "naissance": str(e.naissance) if e.naissance else None,
                "etat_civil": e.etat_civil,
                "contact": e.contact,
            }
            for e in encadreurs
        ],
        "commentaires": (
            {c.section: c.texte for c in commentaires} if commentaires else {}
        ),
        "conclusion": conclusion.texte if conclusion else None,
        "signataires": {s.role: s.nom for s in signataires} if signataires else {},
    }


def _model_to_dict(model_instance) -> dict:
    """Convertit une instance SQLAlchemy en dictionnaire (exclut id et FK)."""
    if model_instance is None:
        return {}
    result = {}
    for col in model_instance.__table__.columns:
        if col.name not in ("id", "rapport_id"):
            val = getattr(model_instance, col.name)
            if isinstance(val, datetime):
                val = str(val)
            result[col.name] = val
    return result


def _populate_template(template_df: pd.DataFrame, data: dict) -> pd.DataFrame:
    """
    Peuple le template Excel avec les données du rapport.
    Utilise le column_mapping.json pour trouver les bonnes colonnes.
    """
    import json

    mapping_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "config"
        / "column_mapping.json"
    )
    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    # Créer une copie du template (ligne 0 = headers, ligne 1+ = données)
    df = template_df.copy()

    # Nous peuplons uniquement la ligne 1 (première ligne de données après les headers)
    data_row_idx = 1

    # 1. Métadonnées
    meta_map = mapping.get("metadata", {})
    _write_cell(
        df,
        data_row_idx,
        meta_map.get("date_soumission"),
        datetime.utcnow().strftime("%b %d, %Y"),
    )
    _write_cell(
        df,
        data_row_idx,
        meta_map.get("coordination_nom"),
        data["metadata"].get("coordination_nom"),
    )
    _write_cell(df, data_row_idx, meta_map.get("annee"), data["metadata"].get("annee"))
    _write_cell(
        df, data_row_idx, meta_map.get("trimestre"), data["metadata"].get("trimestre")
    )
    _write_cell(
        df,
        data_row_idx,
        meta_map.get("coordination_adresse"),
        data["metadata"].get("coordination_adresse"),
    )
    _write_cell(
        df,
        data_row_idx,
        meta_map.get("coordination_email"),
        data["metadata"].get("coordination_email"),
    )
    _write_cell(
        df,
        data_row_idx,
        meta_map.get("coordination_telephone"),
        data["metadata"].get("coordination_telephone"),
    )

    # 2. Paroisses (section répétable)
    _populate_repeatable_section(
        df, data_row_idx, mapping, "paroisses", data.get("paroisses", [])
    )

    # 3. Sections simples (activités)
    for section_key in [
        "activite_pastorale",
        "activite_prophetique",
        "medecine_homme",
        "activite_dos",
        "activite_musique",
        "activite_jeunesse",
    ]:
        section_data = data.get(section_key, {})
        section_cfg = mapping.get(section_key, {})
        fields_map = section_cfg.get("_fields", {})
        for internal_key, excel_suffix in fields_map.items():
            value = section_data.get(internal_key)
            # Construire le nom exact de colonne
            section_prefix = section_cfg.get("_section", "")
            col_name = f"{section_prefix} >> {excel_suffix}"
            _write_cell_by_header(df, data_row_idx, col_name, value)

    # 4. Mariages
    _populate_repeatable_section(
        df, data_row_idx, mapping, "mariages", data.get("mariages", [])
    )

    # 5. Formations
    for form_type, form_list in _group_formations(data.get("formations", [])):
        form_cfg = mapping.get("formations", {}).get(form_type, {})
        if form_cfg:
            _populate_repeatable_section(df, data_row_idx, form_cfg, None, form_list)

    # 6. Conclusion
    conclusion_cfg = mapping.get("conclusion", {})
    _write_cell_by_header(
        df, data_row_idx, conclusion_cfg.get("_field"), data.get("conclusion")
    )

    # 7. Signataires
    sign_data = data.get("signataires", {})
    sign_cfg = mapping.get("signataires", {}).get("_fields", {})
    for role, name in sign_data.items():
        col_target = sign_cfg.get(role)
        if col_target:
            _write_cell_by_header(df, data_row_idx, col_target, name)

    return df


def _write_cell(
    df: pd.DataFrame, row: int, col_name: Optional[str], value: Any
) -> None:
    """Écrit une valeur dans une cellule si le nom de colonne est trouvé."""
    if col_name is None or value is None:
        return

    # Chercher la colonne dont le header correspond
    for col_idx in range(df.shape[1]):
        header = (
            str(df.iloc[0, col_idx]).strip() if pd.notna(df.iloc[0, col_idx]) else ""
        )
        if header.lower() == col_name.lower().strip():
            df.iloc[row, col_idx] = value
            return


def _write_cell_by_header(
    df: pd.DataFrame, row: int, header_target: str, value: Any
) -> None:
    """Écrit une valeur en cherchant le header exact."""
    if header_target is None or value is None:
        return
    target = header_target.lower().strip()
    for col_idx in range(df.shape[1]):
        header = (
            str(df.iloc[0, col_idx]).strip() if pd.notna(df.iloc[0, col_idx]) else ""
        )
        if header.lower() == target:
            df.iloc[row, col_idx] = value
            return


def _populate_repeatable_section(
    df: pd.DataFrame,
    row: int,
    mapping_or_cfg,
    section_key: str,
    items: Optional[list],
) -> None:
    """Peuple une section répétable dans le template."""
    if isinstance(mapping_or_cfg, dict) and section_key:
        cfg = mapping_or_cfg.get(section_key, {})
    else:
        cfg = mapping_or_cfg

    if items is None:
        return

    section_prefix = cfg.get("_section", "")
    fields_map = cfg.get("_fields", {})

    for i, item in enumerate(items):
        item_num = i + 1
        for internal_key, excel_suffix in fields_map.items():
            value = item.get(internal_key)
            if value is not None:
                col_name = f"{section_prefix} >> {item_num}. >> {excel_suffix}"
                _write_cell_by_header(df, row, col_name, value)


def _group_formations(formations: list) -> list[tuple[str, list]]:
    """Groupe les formations par type."""
    groups: dict[str, list] = {}
    for f in formations:
        ftype = f.get("type", "").lower()
        if ftype not in groups:
            groups[ftype] = []
        groups[ftype].append(f)
    return list(groups.items())


def _export_simple_excel(data: dict, output_path: Optional[Path] = None) -> Path:
    """
    Export simple sans modèle (fallback).
    """
    if output_path is None:
        output_path = Path(tempfile.mktemp(suffix=".xlsx"))

    rows: list[dict] = []

    # Aplatir les données en une seule ligne
    flat: dict[str, Any] = {}
    flat["Coordination"] = data["metadata"].get("coordination_nom")
    flat["Année"] = data["metadata"].get("annee")
    flat["Trimestre"] = data["metadata"].get("trimestre")
    flat["Conclusion"] = data.get("conclusion")

    # Ajouter les activités
    for section in [
        "activite_pastorale",
        "activite_prophetique",
        "medecine_homme",
        "activite_dos",
        "activite_musique",
        "activite_jeunesse",
    ]:
        section_data = data.get(section, {})
        for k, v in section_data.items():
            flat[f"{section}.{k}"] = v

    rows.append(flat)

    result_df = pd.DataFrame(rows)
    result_df.to_excel(output_path, index=False, engine="openpyxl")
    return output_path
