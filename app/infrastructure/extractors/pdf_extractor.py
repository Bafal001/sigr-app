"""
Extracteur PDF — Extraction de texte et tableaux depuis des fichiers PDF.
Utilise pdfplumber pour les PDF textuels.
"""

from pathlib import Path
from typing import Optional


def extract_text_from_pdf(file_path: Path) -> str:
    """
    Extrait le texte complet d'un fichier PDF.

    Args:
        file_path: Chemin vers le fichier PDF.

    Returns:
        Texte extrait (peut être vide si le PDF est uniquement une image/scanné).

    Raises:
        FileNotFoundError: Si le fichier n'existe pas.
        ValueError: Si le fichier n'est pas un PDF valide.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")

    if file_path.suffix.lower() != ".pdf":
        raise ValueError(f"Le fichier n'est pas un PDF : {file_path}")

    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber n'est pas installé. Exécutez : pip install pdfplumber"
        )

    full_text_parts: list[str] = []

    with pdfplumber.open(str(file_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            # Extraction du texte brut
            text = page.extract_text()
            if text:
                full_text_parts.append(f"--- Page {page_num} ---\n{text}")

            # Extraction des tableaux
            tables = page.extract_tables()
            if tables:
                for table_idx, table in enumerate(tables, start=1):
                    table_text = _format_table(table, page_num, table_idx)
                    if table_text:
                        full_text_parts.append(table_text)

    return "\n\n".join(full_text_parts)


def is_pdf_scanned(file_path: Path, text_threshold: int = 100) -> bool:
    """
    Détecte si un PDF est scanné (image) plutôt que textuel.

    Un PDF est considéré comme scanné si le texte extrait est très court
    (moins de `text_threshold` caractères).

    Args:
        file_path: Chemin vers le fichier PDF.
        text_threshold: Seuil de caractères en dessous duquel on considère
                        le PDF comme scanné.

    Returns:
        True si le PDF est probablement scanné (peu ou pas de texte).
    """
    text = extract_text_from_pdf(file_path)
    # Nettoyer les whitespaces
    cleaned = text.strip()
    return len(cleaned) < text_threshold


def _format_table(table: list[list[Optional[str]]], page: int, table_idx: int) -> str:
    """
    Formate un tableau extrait en texte lisible.

    Args:
        table: Liste de lignes, chaque ligne étant une liste de cellules.
        page: Numéro de page.
        table_idx: Index du tableau sur la page.

    Returns:
        Représentation textuelle du tableau.
    """
    if not table:
        return ""

    lines: list[str] = [f"--- Tableau {table_idx} (Page {page}) ---"]

    for row in table:
        # Filtrer les cellules None et les joindre
        cells = [str(cell).strip() if cell is not None else "" for cell in row]
        # Ignorer les lignes entièrement vides
        if any(cells):
            lines.append(" | ".join(cells))

    return "\n".join(lines)
