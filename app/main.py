"""
SIGR - Système Intelligent de Gestion des Rapports
Point d'entrée principal de l'application FastAPI.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Chargement des variables d'environnement
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Gestion du cycle de vie de l'application.
    - Startup : initialisation des connexions, vérifications.
    - Shutdown : fermeture propre des ressources.
    """
    # Startup
    print("🚀 SIGR - Démarrage de l'application...")
    yield
    # Shutdown
    print("🛑 SIGR - Arrêt de l'application.")


app = FastAPI(
    title="SIGR - Système Intelligent de Gestion des Rapports",
    description=(
        "API d'import, extraction IA et validation "
        "des rapports trimestriels de supervision."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - À restreindre en production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Enregistrement des routeurs
from app.web.routes.pages import router as pages_router
from app.web.routes.upload import router as upload_router

app.include_router(upload_router)
app.include_router(pages_router)

# Fichiers statiques (CSS, JS, images)
STATIC_DIR = Path(__file__).resolve().parent / "web" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Endpoint racine - Vérification que l'API est en ligne."""
    return {
        "message": "Bienvenue sur l'API SIGR",
        "version": "0.1.0",
        "status": "online",
    }


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check pour monitoring."""
    return {"status": "healthy"}
