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
    # 1. Extraire le texte brut
    raw_text = _extract_raw_text(file_path, file_type)

    if not raw_text or not raw_text.strip():
        # Fichier vide ou illisible
        return [
            ReportInReview(
                row_index=0,
                validation_status="erreur_extraction",
                raw_data={"error": "Aucun texte n'a pu être extrait du fichier."},
            )
        ]

    # 2. Appeler le LLM
    try:
        from app.infrastructure.llm.llm_client import create_llm_client_from_settings

        client = create_llm_client_from_settings()
        json_data = client.extract_json_from_text(raw_text)
    except ValueError as e:
        # Erreur de parsing JSON
        return [
            ReportInReview(
                row_index=0,
                validation_status="erreur_llm",
                raw_data={"error": str(e), "raw_text_preview": raw_text[:500]},
            )
        ]
    except Exception as e:
        return [
            ReportInReview(
                row_index=0,
                validation_status="erreur_api",
                raw_data={
                    "error": f"Erreur API LLM : {str(e)}",
                    "raw_text_preview": raw_text[:500],
                },
            )
        ]

    # 3. Construire le ReportInReview
    metadata = json_data.get("metadata", {})
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
        # Paroisse : chercher une colonne qui contient "paroisse" et "nom" ou "1."
        paroisse_nom = _find_smart(
            row_dict, ["paroisse >> 1.", "paroisses >> 1. >> paroisse"]
        ) or _find_smart(row_dict, ["paroisse", "église", "eglise"])

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


def _find_smart(row_dict: dict, keywords: list[str]) -> Optional[str]:
    """
    Recherche intelligente : trouve la première colonne dont le nom
    contient l'un des mots-clés (insensible à la casse).
    """
    if not row_dict:
        return None
    for key, value in row_dict.items():
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
