"""
Mapper Dynamique — Transforme les données brutes (JSON LLM ou DataFrame Excel)
en dictionnaires prêts pour l'insertion en base SQLite.

Lit le fichier config/column_mapping.json pour faire la correspondance
entre les clés internes et les noms de colonnes Excel.

Respecte Clean Architecture : logique métier pure, sans dépendances web/DB.
"""

import json
from pathlib import Path
from typing import Any, Optional

# Chemin vers le fichier de mapping
_MAPPING_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "config"
    / "column_mapping.json"
)

# Cache du mapping chargé
_mapping_cache: Optional[dict] = None


def _load_mapping() -> dict:
    """Charge le fichier column_mapping.json (avec cache)."""
    global _mapping_cache
    if _mapping_cache is None:
        with open(_MAPPING_PATH, "r", encoding="utf-8") as f:
            _mapping_cache = json.load(f)
    return _mapping_cache


def get_section_mapping(section_name: str) -> Optional[dict]:
    """
    Récupère la configuration de mapping pour une section donnée.

    Args:
        section_name: Nom de la section (ex: 'activite_pastorale', 'paroisses').

    Returns:
        Configuration de mapping ou None si la section n'existe pas.
    """
    mapping = _load_mapping()
    return mapping.get(section_name)


def map_excel_row_to_db(row_dict: dict) -> dict:
    """
    Transforme une ligne Excel brute (DataFrame → dict) en dictionnaire
    structuré prêt pour l'insertion en base de données.

    Le mapping est piloté par column_mapping.json qui définit :
    - Pour chaque section, le préfixe de colonne Excel
    - Les champs à mapper et leurs noms de colonnes Excel

    Args:
        row_dict: Dictionnaire brut d'une ligne Excel
                  (clés = noms de colonnes Excel, valeurs = données).

    Returns:
        Dictionnaire structuré avec les sections SIGR.
    """
    mapping = _load_mapping()
    result: dict[str, Any] = {}

    # 1. Métadonnées
    meta_mapping = mapping.get("metadata", {}).get(
        "_fields", mapping.get("metadata", {})
    )
    result["metadata"] = _extract_fields(meta_mapping, row_dict)

    # 2. Sections répétables (paroisses, mariages, etc.)
    for section_key in [
        "paroisses",
        "mariages",
        "patrimoine_immobilier",
        "dirigeant_musical",
        "encadreur_jeunesse",
    ]:
        section_cfg = mapping.get(section_key)
        if section_cfg and section_cfg.get("_repeat"):
            result[section_key] = _extract_repeatable_section(section_cfg, row_dict)

    # 3. Sections simples (1-1 avec le rapport)
    for section_key in [
        "activite_pastorale",
        "activite_prophetique",
        "medecine_homme",
        "activite_dos",
        "activite_musique",
        "activite_jeunesse",
        "inventaire_intendance",
    ]:
        section_cfg = mapping.get(section_key)
        if section_cfg:
            fields_map = section_cfg.get("_fields", {})
            result[section_key] = _extract_fields(fields_map, row_dict)

    # 4. Formations (6 types)
    formations_cfg = mapping.get("formations", {})
    result["formations"] = []
    for form_type in [
        "mibali",
        "bolingo",
        "basi",
        "basakoli",
        "disciples",
        "jeunesses",
    ]:
        type_cfg = formations_cfg.get(form_type, {})
        if type_cfg.get("_repeat"):
            items = _extract_repeatable_section(type_cfg, row_dict)
            for item in items:
                item["type"] = form_type.capitalize()
            result["formations"].extend(items)

    # 5. Commentaires
    commentaires_cfg = mapping.get("commentaires", {}).get("_fields", {})
    result["commentaires"] = _extract_fields(commentaires_cfg, row_dict)

    # 6. Conclusion
    conclusion_cfg = mapping.get("conclusion", {})
    conclusion_field = conclusion_cfg.get("_field", "")
    if conclusion_field and conclusion_field in row_dict:
        result["conclusion"] = row_dict[conclusion_field]
    else:
        result["conclusion"] = None

    # 7. Signataires
    signataires_cfg = mapping.get("signataires", {}).get("_fields", {})
    result["signataires"] = _extract_fields(signataires_cfg, row_dict)

    return result


def map_llm_json_to_db(llm_json: dict) -> dict:
    """
    Transforme le JSON produit par le LLM en dictionnaire prêt pour la DB.

    Le JSON du LLM est déjà structuré (metadata, activite_pastorale, etc.),
    donc on le valide et on le nettoie simplement.

    Args:
        llm_json: JSON produit par le LLM.

    Returns:
        Dictionnaire nettoyé et validé.
    """
    return _clean_llm_json(llm_json)


def _extract_fields(
    fields_map: dict[str, str],
    row_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    Extrait les champs d'une ligne brute en utilisant le mapping.

    Args:
        fields_map: Mapping clé_interne → nom_colonne_excel (suffixe).
        row_dict: Dictionnaire brut de la ligne.

    Returns:
        Dictionnaire avec les clés internes et les valeurs extraites.
    """
    result: dict[str, Any] = {}

    for internal_key, excel_suffix in fields_map.items():
        if excel_suffix is None:
            result[internal_key] = None
            continue

        # Chercher la colonne Excel correspondante
        value = _find_column_value(row_dict, excel_suffix)
        result[internal_key] = _cast_value(value)

    return result


def _extract_repeatable_section(
    section_cfg: dict,
    row_dict: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Extrait les entrées d'une section répétable (ex: paroisses 1..25).

    Args:
        section_cfg: Configuration de la section (_section, _repeat, _max, _fields).
        row_dict: Dictionnaire brut de la ligne.

    Returns:
        Liste de dictionnaires (un par occurrence non vide).
    """
    section_prefix = section_cfg.get("_section", "")
    max_items = section_cfg.get("_max", 1)
    fields_map = section_cfg.get("_fields", {})

    items: list[dict[str, Any]] = []

    for i in range(1, max_items + 1):
        item: dict[str, Any] = {}
        has_data = False

        for internal_key, excel_suffix in fields_map.items():
            # Construire le nom complet de la colonne Excel
            full_col_name = f"{section_prefix} >> {i}. >> {excel_suffix}"
            value = _find_column_value(row_dict, full_col_name)
            if value is not None:
                has_data = True
            item[internal_key] = _cast_value(value)

        # N'ajouter que si au moins un champ est renseigné
        if has_data:
            items.append(item)

    return items


def _find_column_value(row_dict: dict[str, Any], target: str) -> Any:
    """
    Trouve la valeur dans row_dict correspondant au nom de colonne cible.
    La recherche est insensible à la casse et aux espaces.

    Args:
        row_dict: Dictionnaire brut.
        target: Nom de colonne recherché (ex: "Bandimi Hommes >> Nombre").

    Returns:
        Valeur trouvée ou None.
    """
    target_lower = target.lower().strip()

    # Recherche exacte d'abord
    if target in row_dict:
        return row_dict[target]

    # Recherche insensible à la casse
    for key, value in row_dict.items():
        if key.lower().strip() == target_lower:
            return value

    # Recherche partielle (le suffixe est contenu dans la clé)
    for key, value in row_dict.items():
        if target_lower in key.lower():
            return value

    return None


def _cast_value(value: Any) -> Any:
    """
    Convertit une valeur en type approprié (int, float, str, None).

    - "Nul", "N/A", "", None → None
    - "123" → 123 (int)
    - "12.5" → 12.5 (float)
    - Autres → str
    """
    if value is None:
        return None

    if isinstance(value, (int, float, bool)):
        return value

    if not isinstance(value, str):
        return str(value)

    stripped = value.strip()

    # Valeurs nulles explicites
    if stripped.lower() in ("", "nul", "null", "none", "n/a", "na", "-"):
        return None

    # Tenter de convertir en entier
    try:
        return int(stripped)
    except ValueError:
        pass

    # Tenter de convertir en float
    try:
        return float(stripped)
    except ValueError:
        pass

    return stripped


def _clean_llm_json(data: dict) -> dict:
    """
    Nettoie le JSON du LLM : supprime les champs null inutiles,
    convertit les types, etc.
    """
    cleaned: dict[str, Any] = {}

    for key, value in data.items():
        if isinstance(value, dict):
            cleaned[key] = {k: _cast_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            cleaned_list = []
            for item in value:
                if isinstance(item, dict):
                    cleaned_list.append({k: _cast_value(v) for k, v in item.items()})
                else:
                    cleaned_list.append(_cast_value(item))
            cleaned[key] = cleaned_list
        else:
            cleaned[key] = _cast_value(value)

    return cleaned
