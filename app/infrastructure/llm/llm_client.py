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
# Chargement des prompts
# ---------------------------------------------------------------------------
_PROMPT_DIR = Path(__file__).resolve().parent
_META_PROMPT: Optional[str] = None
_ITERATION_TEMPLATE: Optional[str] = None


def _load_meta_prompt() -> str:
    """Charge le méta-prompt (envoyé une seule fois)."""
    global _META_PROMPT
    if _META_PROMPT is None:
        _META_PROMPT = (_PROMPT_DIR / "meta_prompt.txt").read_text(encoding="utf-8")
    return _META_PROMPT


def _load_iteration_template() -> str:
    """Charge le template de prompt d'itération."""
    global _ITERATION_TEMPLATE
    if _ITERATION_TEMPLATE is None:
        _ITERATION_TEMPLATE = (_PROMPT_DIR / "iteration_prompt.txt").read_text(
            encoding="utf-8"
        )
    return _ITERATION_TEMPLATE


# Liste des tables dans l'ordre
TABLE_IDS = [
    "T01_metadata",
    "T02_paroisses",
    "T03_activite_pastorale",
    "T04_activite_prophetique",
    "T05_medecine_homme",
    "T06_mariages",
    "T07_formations",
    "T08_inventaire_intendance",
    "T09_patrimoine_immobilier",
    "T10_activite_dos",
    "T11_activite_musique",
    "T12_dirigeants_musicaux",
    "T13_activite_jeunesse",
    "T14_encadreurs_jeunesse",
    "T15_commentaires",
    "T16_conclusion",
    "T17_signataires",
]


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
        Extraction ITÉRATIVE : méta-prompt + 17 appels (un par table).
        Résout le problème de dépassement de tokens.
        """
        meta = _load_meta_prompt()
        template = _load_iteration_template()

        result: dict = {}
        failed: list[str] = []

        for i, table_id in enumerate(TABLE_IDS):
            print(f"  🔄 {table_id} ({i+1}/17)...")
            try:
                data = self._extract_single_table(table_id, template, text, meta)
                if data:
                    # La réponse est {"Txx_...": {...}, "points_a_verifier": [...]}
                    for k, v in data.items():
                        if (
                            k.startswith("T")
                            and not k.endswith("_error")
                            and k != "points_a_verifier"
                        ):
                            result[k] = v
            except Exception as e:
                failed.append(f"{table_id}: {e}")

        if failed:
            result["_extraction_errors"] = failed

        return result

    def _extract_single_table(
        self, table_id: str, template: str, full_text: str, meta_prompt: str
    ) -> Optional[dict]:
        """Extrait UNE SEULE table avec retry."""
        prompt = template.format(table_id=table_id)
        # Limiter le texte pour cette itération
        text_snippet = full_text[:25000]

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": meta_prompt},
                        {
                            "role": "user",
                            "content": f"{text_snippet}\n\n---\n\n{prompt}",
                        },
                    ],
                    max_tokens=min(self.max_tokens, 2048),
                    temperature=self.temperature,
                )
                raw = response.choices[0].message.content
                if raw is None:
                    raise ValueError("Réponse vide")
                return _parse_llm_json(raw)
            except json.JSONDecodeError:
                if attempt < self.max_retries:
                    time.sleep(2**attempt)
            except Exception as e:
                err = str(e).lower()
                if any(kw in err for kw in ("429", "rate", "timeout", "503", "502")):
                    if attempt < self.max_retries:
                        time.sleep(2**attempt)
                        continue
                raise
        return None


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
