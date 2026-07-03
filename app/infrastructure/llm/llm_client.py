"""
Client LLM — Interface avec l'API DeepSeek (compatible OpenAI SDK).
Gère les appels, la retry logic, et les timeouts.
"""

import json
import time
from pathlib import Path
from typing import Optional

from openai import OpenAI

# ---------------------------------------------------------------------------
# Chargement du prompt système
# ---------------------------------------------------------------------------
_PROMPT_PATH = Path(__file__).resolve().parent / "prompts.txt"
_SYSTEM_PROMPT: Optional[str] = None


def _load_system_prompt() -> str:
    """Charge le prompt système depuis le fichier prompts.txt (avec cache)."""
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        _SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")
    return _SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Client LLM
# ---------------------------------------------------------------------------
class LLMClient:
    """
    Client pour l'API DeepSeek (compatible OpenAI SDK).
    Gère les appels avec retry automatique en cas d'erreur.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-pro",
        max_tokens: int = 4096,
        temperature: float = 0.1,
        max_retries: int = 3,
        timeout: float = 120.0,
    ):
        """
        Args:
            api_key: Clé API DeepSeek.
            base_url: URL de base de l'API.
            model: Nom du modèle à utiliser.
            max_tokens: Nombre maximum de tokens en sortie.
            temperature: Température (0-2). Basse = plus déterministe.
            max_retries: Nombre de tentatives en cas d'échec.
            timeout: Timeout par requête en secondes.
        """
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout = timeout

        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    def extract_json_from_text(self, text: str) -> dict:
        """
        Envoie le texte au LLM et récupère le JSON structuré.

        Args:
            text: Texte brut extrait du document.

        Returns:
            Dictionnaire JSON structuré selon le schéma SIGR.

        Raises:
            ValueError: Si le LLM retourne un JSON invalide.
            RuntimeError: Si l'API échoue après toutes les tentatives.
        """
        system_prompt = _load_system_prompt()

        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )

                raw_output = response.choices[0].message.content
                if raw_output is None:
                    raise ValueError("Le LLM a retourné une réponse vide.")

                # Nettoyer et parser le JSON
                return _parse_llm_json(raw_output)

            except json.JSONDecodeError as e:
                last_error = e
                if attempt < self.max_retries:
                    wait = 2**attempt  # Backoff exponentiel : 2, 4, 8 secondes
                    time.sleep(wait)
                    continue
                raise ValueError(
                    f"Le LLM n'a pas retourné un JSON valide "
                    f"après {self.max_retries} tentatives : {e}"
                ) from e

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Erreurs récupérables (rate limit, timeout, serveur)
                if any(
                    kw in error_str
                    for kw in (
                        "429",
                        "rate limit",
                        "timeout",
                        "503",
                        "502",
                        "server error",
                    )
                ):
                    if attempt < self.max_retries:
                        wait = 2**attempt
                        time.sleep(wait)
                        continue

                # Erreur non récupérable
                raise RuntimeError(
                    f"Erreur API LLM (tentative {attempt}/{self.max_retries}) : {e}"
                ) from e

        # Ne devrait jamais arriver, mais sécurité
        raise RuntimeError(
            f"Échec après {self.max_retries} tentatives. "
            f"Dernière erreur : {last_error}"
        )


def _parse_llm_json(raw: str) -> dict:
    """
    Parse la sortie brute du LLM en dictionnaire JSON.

    Gère les cas où le LLM encapsule le JSON dans des backticks markdown.
    """
    raw = raw.strip()

    # Supprimer les backticks markdown si présents
    if raw.startswith("```"):
        # Trouver la fin des backticks
        lines = raw.split("\n")
        # Supprimer la première ligne (```json ou ```)
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Supprimer la dernière ligne (```)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)

    # Parser le JSON
    return json.loads(raw)


def create_llm_client_from_settings() -> LLMClient:
    """
    Crée un LLMClient à partir de la configuration de l'application.

    Returns:
        Instance de LLMClient configurée.
    """
    from app.infrastructure.config.settings import get_settings

    settings = get_settings()

    api_key = settings.active_llm_key
    if not api_key:
        raise ValueError(
            "Clé API LLM non configurée. "
            "Définissez DEEPSEEK_API_KEY ou LLM_API_KEY dans .env"
        )

    return LLMClient(
        api_key=api_key,
        base_url=settings.llm_api_base_url,
        model=settings.llm_model,
        max_tokens=settings.llm_max_tokens,
        temperature=settings.llm_temperature,
    )
