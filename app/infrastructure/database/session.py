"""
Base de données — Configuration du moteur SQLAlchemy et de la session.
"""

from pathlib import Path
from typing import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.config.settings import get_settings

# Création du dossier data/ si nécessaire
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

settings = get_settings()

# Moteur SQLAlchemy
engine: Engine = create_engine(
    settings.database_url,
    connect_args=(
        {"check_same_thread": False} if "sqlite" in settings.database_url else {}
    ),
    echo=settings.app_debug,
)

# Fabrique de sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dépendance FastAPI : fournit une session SQLAlchemy par requête.
    La session est automatiquement fermée après la requête.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
