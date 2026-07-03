"""
Schémas Pydantic pour l'API — Requêtes, Réponses, Validation.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
class UploadResponse(BaseModel):
    """Réponse après l'upload d'un fichier (potentiellement multi-lignes)."""

    status: str = Field(default="received", examples=["received"])
    file_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Identifiant unique du fichier uploadé",
    )
    original_filename: str = Field(description="Nom original du fichier")
    file_type: str = Field(description="Extension/type MIME détecté")
    rows_detected: int = Field(
        default=0, description="Nombre de lignes/rapports détectés dans le fichier"
    )
    uploaded_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Horodatage de l'upload",
    )


# ---------------------------------------------------------------------------
# Rapport en attente de validation (Review)
# ---------------------------------------------------------------------------
class ReportInReview(BaseModel):
    """Un rapport individuel extrait, en attente de validation humaine."""

    row_index: int = Field(
        description="Index de la ligne dans le fichier source (0-based)"
    )
    coordination_nom: Optional[str] = Field(
        default=None, description="Nom de la coordination/supervision"
    )
    annee: Optional[int] = Field(default=None, description="Année du rapport")
    trimestre: Optional[int] = Field(default=None, description="Trimestre (1-4)")
    paroisse_nom: Optional[str] = Field(
        default=None, description="Nom de la première paroisse (aperçu)"
    )
    raw_data: dict = Field(
        default_factory=dict,
        description="Données brutes extraites de la ligne (pour validation)",
    )
    validation_status: str = Field(
        default="en_attente",
        examples=["en_attente"],
        description="Statut de validation : en_attente, valide, rejete",
    )


# ---------------------------------------------------------------------------
# Détail d'un fichier uploadé
# ---------------------------------------------------------------------------
class FileDetail(BaseModel):
    """Informations détaillées sur un fichier uploadé."""

    file_id: str
    original_filename: str
    file_type: str
    rows_detected: int
    uploaded_at: datetime
    reports: list[ReportInReview] = Field(
        default_factory=list,
        description="Liste des rapports extraits du fichier",
    )
    status: str = Field(default="pending_validation")


# ---------------------------------------------------------------------------
# Réponse générique
# ---------------------------------------------------------------------------
class APIResponse(BaseModel):
    """Enveloppe standard pour toutes les réponses API."""

    success: bool = True
    message: str = "OK"
    data: Optional[dict | list] = None
