"""
Routes pour les pages HTML de l'interface utilisateur.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter(tags=["Pages"])

# Configuration des templates Jinja2
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/upload", response_class=HTMLResponse, summary="Page d'upload")
async def upload_page(request: Request) -> HTMLResponse:
    """Page d'accueil avec zone de Drag & Drop pour l'upload de fichiers."""
    return templates.TemplateResponse("upload.html", {"request": request})


@router.get(
    "/validation/{file_id}", response_class=HTMLResponse, summary="Page de validation"
)
async def validation_page(request: Request, file_id: str) -> HTMLResponse:
    """Page de validation humaine pour un fichier uploadé (traitement par lot)."""
    return templates.TemplateResponse(
        "validation.html",
        {"request": request, "file_id": file_id},
    )
