"""
Module OCR — Reconnaissance optique de caractères pour les PDF scannés.
Utilise pytesseract + Pillow pour l'OCR.
"""

from pathlib import Path

# pip install pytesseract Pillow pdf2image
# nécessite aussi tesseract-ocr installé sur le système


def extract_text_via_ocr(file_path: Path, lang: str = "fra+eng") -> str:
    """
    Extrait le texte d'un PDF scanné via OCR (pytesseract).

    Convertit chaque page du PDF en image, puis applique l'OCR.

    Args:
        file_path: Chemin vers le fichier PDF scanné.
        lang: Langues pour Tesseract (ex: 'fra+eng' pour français + anglais).

    Returns:
        Texte reconnu par OCR.

    Raises:
        ImportError: Si les dépendances OCR ne sont pas installées.
        RuntimeError: Si Tesseract n'est pas installé sur le système.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")

    # Vérifier les dépendances Python
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        raise ImportError(
            "Dépendances OCR manquantes. Exécutez :\n"
            "  pip install pytesseract Pillow pdf2image\n"
            "  sudo apt install tesseract-ocr tesseract-ocr-fra poppler-utils"
        )

    # Vérifier que Tesseract est installé
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        raise RuntimeError(
            "Tesseract OCR n'est pas installé ou introuvable.\n"
            "  sudo apt install tesseract-ocr tesseract-ocr-fra"
        )

    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise ImportError(
            "pdf2image n'est pas installé. Exécutez : pip install pdf2image"
        )

    # Convertir les pages du PDF en images
    try:
        images = convert_from_path(str(file_path), dpi=300)
    except Exception as e:
        raise RuntimeError(
            f"Impossible de convertir le PDF en images : {e}\n"
            "Vérifiez que poppler-utils est installé : sudo apt install poppler-utils"
        )

    text_parts: list[str] = []

    for page_num, image in enumerate(images, start=1):
        # OCR sur l'image
        page_text = pytesseract.image_to_string(image, lang=lang)
        if page_text.strip():
            text_parts.append(f"--- Page {page_num} (OCR) ---\n{page_text.strip()}")

    return "\n\n".join(text_parts)


def extract_text_from_pdf_with_ocr_fallback(file_path: Path) -> tuple[str, str]:
    """
    Tente l'extraction texte d'abord, puis bascule sur l'OCR si nécessaire.

    Args:
        file_path: Chemin vers le fichier PDF.

    Returns:
        Tuple (texte_extrait, méthode_utilisée)
        méthode_utilisée = 'pdfplumber' | 'ocr'
    """
    # Essayer d'abord l'extraction texte normale
    from app.infrastructure.extractors.pdf_extractor import (
        extract_text_from_pdf,
        is_pdf_scanned,
    )

    if file_path.suffix.lower() == ".pdf":
        if is_pdf_scanned(file_path):
            # PDF scanné → utiliser OCR
            text = extract_text_via_ocr(file_path)
            return text, "ocr"
        else:
            # PDF textuel
            text = extract_text_from_pdf(file_path)
            return text, "pdfplumber"
    else:
        # Pour les images directes (futur support)
        text = extract_text_via_ocr(file_path)
        return text, "ocr"
