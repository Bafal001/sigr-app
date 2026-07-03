"""
Base déclarative SQLAlchemy — toutes les classes de modèles en héritent.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles SQLAlchemy."""

    pass
