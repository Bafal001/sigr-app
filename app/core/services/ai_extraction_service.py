"""
Service d'extraction IA — Orchestration du pipeline d'extraction.
Respecte Clean Architecture : logique métier pure.
"""

import json
from pathlib import Path
from typing import Optional

from app.core.models.schemas import ReportInReview

# Types de fichiers qui utilisent le LLM
_LLM_FILE_TYPES: set[str] = {"pdf", "word", "text"}

# Types de fichiers structurés (pas de LLM)
_STRUCTURED_FILE_TYPES: set[str] = {"excel", "csv"}


def extract_reports_from_file(
    file_path: Path,
    file_type: str,
) -> list[ReportInReview]:
    """
    Extrait les rapports d'un fichier uploadé.

    - Pour PDF/Word : extraction texte → LLM → JSON → ReportInReview
    - Pour Excel/CSV : saute le LLM, retourne les données brutes (mapping Phase 5)

    Args:
        file_path: Chemin vers le fichier uploadé.
        file_type: Type détecté ('pdf', 'word', 'excel', 'csv', 'text').

    Returns:
        Liste de ReportInReview (un seul pour PDF/Word, plusieurs pour Excel).

    Raises:
        ValueError: Si le type de fichier n'est pas supporté.
    """
    if file_type in _LLM_FILE_TYPES:
        return _extract_via_llm(file_path, file_type)
    elif file_type in _STRUCTURED_FILE_TYPES:
        return _extract_structured(file_path, file_type)
    else:
        raise ValueError(
            f"Type de fichier non supporté pour l'extraction : {file_type}"
        )


def _extract_via_llm(file_path: Path, file_type: str) -> list[ReportInReview]:
    """
    Pipeline LLM : extraction texte → LLM → parsing JSON → validation.

    Args:
        file_path: Chemin du fichier.
        file_type: 'pdf', 'word', ou 'text'.

    Returns:
        Liste avec un seul ReportInReview contenant les données extraites.
    """
    # 1. Extraire le texte brut (PAS de troncation, l'itératif gère)
    raw_text = _extract_raw_text(file_path, file_type)

    if not raw_text or not raw_text.strip():
        return [
            ReportInReview(
                row_index=0,
                validation_status="erreur_extraction",
                raw_data={"error": "Aucun texte n'a pu être extrait du fichier."},
            )
        ]

    # 2. Appeler le LLM en mode ITÉRATIF (17 appels, un par table)
    try:
        from app.infrastructure.llm.llm_client import create_llm_client_from_settings

        client = create_llm_client_from_settings()
        llm_result = client.extract_json_from_text(raw_text)
    except Exception as e:
        return [
            ReportInReview(
                row_index=0,
                validation_status="erreur_api",
                raw_data={"error": f"Erreur API LLM : {str(e)}"},
            )
        ]

    # 3. Remapper Txx_... → noms de sections standard
    TABLE_MAP = {
        "T01_metadata": "metadata",
        "T02_paroisses": "paroisses",
        "T03_activite_pastorale": "activite_pastorale",
        "T04_activite_prophetique": "activite_prophetique",
        "T05_medecine_homme": "medecine_homme",
        "T06_mariages": "mariages",
        "T07_formations": "formations",
        "T08_inventaire_intendance": "inventaire_intendance",
        "T09_patrimoine_immobilier": "patrimoine_immobilier",
        "T10_activite_dos": "activite_dos",
        "T11_activite_musique": "activite_musique",
        "T12_dirigeants_musicaux": "dirigeants_musicaux",
        "T13_activite_jeunesse": "activite_jeunesse",
        "T14_encadreurs_jeunesse": "encadreurs_jeunesse",
        "T15_commentaires": "commentaires",
        "T16_conclusion": "conclusion",
        "T17_signataires": "signataires",
    }

    json_data: dict = {}
    for t_key, std_key in TABLE_MAP.items():
        if t_key in llm_result:
            json_data[std_key] = llm_result[t_key]
        else:
            json_data[std_key] = (
                None
                if std_key == "conclusion"
                else (
                    []
                    if std_key
                    in (
                        "paroisses",
                        "mariages",
                        "formations",
                        "patrimoine_immobilier",
                        "dirigeants_musicaux",
                        "encadreurs_jeunesse",
                    )
                    else {}
                )
            )

    # Ajouter les erreurs s'il y en a
    if "_extraction_errors" in llm_result:
        json_data["_extraction_errors"] = llm_result["_extraction_errors"]

    # 4. Construire le ReportInReview
    metadata = json_data.get("metadata") or {}
    report = ReportInReview(
        row_index=0,
        coordination_nom=metadata.get("coordination_nom"),
        annee=metadata.get("annee"),
        trimestre=metadata.get("trimestre"),
        raw_data=json_data,
        validation_status="en_attente",
    )

    return [report]


def _extract_structured(file_path: Path, file_type: str) -> list[ReportInReview]:
    """
    Extraction sans LLM pour les fichiers structurés (Excel, CSV).
    Retourne les données brutes — le mapping sera fait à la Phase 5.

    Args:
        file_path: Chemin du fichier.
        file_type: 'excel' ou 'csv'.

    Returns:
        Liste de ReportInReview (une par ligne de données).
    """
    try:
        import pandas as pd
    except ImportError:
        return [
            ReportInReview(
                row_index=0,
                validation_status="erreur_extraction",
                raw_data={"error": "pandas n'est pas installé."},
            )
        ]

    try:
        if file_type == "csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path, sheet_name=0)
    except Exception as e:
        return [
            ReportInReview(
                row_index=0,
                validation_status="erreur_extraction",
                raw_data={"error": f"Erreur de lecture du fichier : {str(e)}"},
            )
        ]

    # Exclure la ligne d'en-tête (index 0) et les lignes entièrement vides
    # Les données commencent à l'index 1 (après les headers)
    data_rows = df.iloc[1:] if len(df) > 1 else df.iloc[0:0]
    data_rows = data_rows.dropna(how="all")

    reports: list[ReportInReview] = []
    for idx, (_, row) in enumerate(data_rows.iterrows()):
        # Convertir la ligne en dictionnaire (en excluant les NaN)
        row_dict = {
            str(k): (v if pd.notna(v) else None) for k, v in row.to_dict().items()
        }

        # Extraire les champs d'aperçu avec recherche intelligente multi-mot-clé
        coordination_nom = _find_smart(
            row_dict,
            [
                "coordination",
                "supervision",
                "coordo",
            ],
        )
        annee = _parse_int_safe(
            _find_smart(
                row_dict,
                [
                    "année",
                    "annee",
                    "exercice",
                    "year",
                ],
            )
        )
        trimestre = _parse_int_safe(
            _find_smart(
                row_dict,
                [
                    "trimestre",
                    "trim",
                ],
            )
        )
        # Paroisse : chercher dans les sous-champs (pattern ">> 1. >> Paroisse")
        paroisse_nom = _find_smart(
            row_dict,
            ["listes des paroisses >> 1. >> paroisse", "paroisses >> 1. >> paroisse"],
            allow_subfields=True,
        ) or _find_smart(
            row_dict,
            ["paroisse >> 1. >> nom", "liste des paroisses >> 1."],
            allow_subfields=True,
        )

        reports.append(
            ReportInReview(
                row_index=idx,
                coordination_nom=coordination_nom,
                annee=annee,
                trimestre=trimestre,
                paroisse_nom=paroisse_nom,
                raw_data=row_dict,
                validation_status="en_attente",
            )
        )

    return reports


def _find_smart(
    row_dict: dict, keywords: list[str], allow_subfields: bool = False
) -> Optional[str]:
    """
    Recherche par mots-clés dans les colonnes.
    Par défaut ignore les colonnes avec '>>' (sous-champs).
    allow_subfields=True pour chercher aussi dans les sous-champs (ex: paroisse).
    """
    if not row_dict:
        return None

    for key, value in row_dict.items():
        if not allow_subfields and ">>" in str(key):
            continue
        key_lower = key.lower().strip()
        for kw in keywords:
            if kw.lower() in key_lower:
                if value is not None and str(value).strip() not in (
                    "",
                    "Nul",
                    "null",
                    "None",
                ):
                    return str(value).strip()
    return None


def _find_value_in_row(row_dict: dict, target: str) -> Optional[str]:
    """Trouve une valeur dans row_dict par correspondance partielle de clé."""
    target_lower = target.lower().strip()
    # Recherche exacte
    if target in row_dict:
        val = row_dict[target]
        return str(val) if val is not None else None
    # Recherche insensible à la casse
    for key, value in row_dict.items():
        if key.lower().strip() == target_lower:
            return str(value) if value is not None else None
    # Recherche partielle
    for key, value in row_dict.items():
        if target_lower in key.lower():
            return str(value) if value is not None else None
    return None


def _parse_int_safe(value: Optional[str]) -> Optional[int]:
    """Convertit une chaîne en entier de manière sécurisée."""
    if value is None:
        return None
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None


def _extract_raw_text(file_path: Path, file_type: str) -> str:
    """
    Extrait le texte brut d'un fichier selon son type.

    Args:
        file_path: Chemin du fichier.
        file_type: 'pdf', 'word', ou 'text'.

    Returns:
        Texte brut extrait.
    """
    if file_type == "pdf":
        from app.infrastructure.extractors.ocr import (
            extract_text_from_pdf_with_ocr_fallback,
        )

        text, method = extract_text_from_pdf_with_ocr_fallback(file_path)
        return text

    elif file_type == "word":
        from app.infrastructure.extractors.docx_extractor import extract_text_from_docx

        return extract_text_from_docx(file_path)

    elif file_type == "text":
        return file_path.read_text(encoding="utf-8", errors="replace")

    else:
        raise ValueError(
            f"Type de fichier non supporté pour l'extraction texte : {file_type}"
        )
