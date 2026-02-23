"""
Centralized Configuration Module for BIMTwinOps Backend.

ALL environment variables are loaded here from backend/.env.
Every other module should import from this module instead of
calling os.getenv() with scattered fallback defaults.

Usage:
    from .config import cfg          # inside the api package
    from api.config import cfg       # from scripts / __main__
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import List

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load .env — try backend/.env first, then root .env as fallback
# ---------------------------------------------------------------------------
_backend_dir = Path(__file__).resolve().parent.parent          # backend/
_root_dir = _backend_dir.parent                                # SMART_BIM/

_env_path = _backend_dir / ".env"
if not _env_path.exists():
    _env_path = _root_dir / ".env"

if _env_path.exists():
    load_dotenv(_env_path, override=False)
    logger.info("Loaded .env from %s", _env_path)
else:
    logger.warning(
        "No .env file found at %s or %s.  Copy .env.example and configure.",
        _backend_dir / ".env",
        _root_dir / ".env",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require(key: str, secret: bool = False) -> str:
    """Return env var or raise with a helpful message."""
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Required environment variable {key} is not set.  "
                           f"Add it to your .env file.")
    return val


def _csv(key: str, default: str = "") -> List[str]:
    """Split an env var on commas / spaces into a list."""
    raw = os.getenv(key, default)
    return [s.strip() for s in raw.replace(",", " ").split() if s.strip()]


# ═══════════════════════════════════════════════════════════════════════════
# Configuration values — single source of truth
# ═══════════════════════════════════════════════════════════════════════════

class _Config:
    """Lazy-loaded configuration singleton.  Access via module-level ``cfg``."""

    # ── Backend Server ────────────────────────────────────────────────────
    @property
    def BACKEND_HOST(self) -> str:
        return os.getenv("BACKEND_HOST", "0.0.0.0")

    @property
    def BACKEND_PORT(self) -> int:
        return int(os.getenv("BACKEND_PORT", "8000"))

    # ── CORS ──────────────────────────────────────────────────────────────
    @property
    def CORS_ORIGINS(self) -> List[str]:
        return _csv("CORS_ORIGINS",
                     "http://localhost:5173,http://127.0.0.1:5173")

    # ── Neo4j ─────────────────────────────────────────────────────────────
    @property
    def NEO4J_URI(self) -> str:
        return os.getenv("NEO4J_URI", "")

    @property
    def NEO4J_USER(self) -> str:
        return os.getenv("NEO4J_USER", "")

    @property
    def NEO4J_PASSWORD(self) -> str:
        return os.getenv("NEO4J_PASSWORD", "")

    @property
    def NEO4J_DATABASE(self) -> str:
        return os.getenv("NEO4J_DATABASE", "neo4j")

    @property
    def neo4j_configured(self) -> bool:
        return bool(self.NEO4J_URI and self.NEO4J_USER and self.NEO4J_PASSWORD)

    # ── Google / Gemini ───────────────────────────────────────────────────
    @property
    def GOOGLE_API_KEY(self) -> str:
        return os.getenv("GOOGLE_API_KEY", "")

    # ── LLM Provider ─────────────────────────────────────────────────────
    @property
    def LLM_PROVIDER(self) -> str:
        return os.getenv("LLM_PROVIDER", "ollama")

    # ── Ollama ────────────────────────────────────────────────────────────
    @property
    def OLLAMA_BASE_URL(self) -> str:
        return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    @property
    def OLLAMA_MODEL(self) -> str:
        return os.getenv("OLLAMA_MODEL", "llama3.2:1b")

    @property
    def OLLAMA_EMBED_MODEL(self) -> str:
        return os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")

    # ── Azure OpenAI ──────────────────────────────────────────────────────
    @property
    def AZURE_OPENAI_ENDPOINT(self) -> str:
        return os.getenv("AZURE_OPENAI_ENDPOINT", "")

    @property
    def AZURE_OPENAI_API_KEY(self) -> str:
        return os.getenv("AZURE_OPENAI_API_KEY", "")

    @property
    def AZURE_OPENAI_DEPLOYMENT(self) -> str:
        return os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    @property
    def AZURE_OPENAI_API_VERSION(self) -> str:
        return os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

    # ── APS (Autodesk Platform Services) ──────────────────────────────────
    @property
    def APS_CLIENT_ID(self) -> str:
        return os.getenv("APS_CLIENT_ID", "")

    @property
    def APS_CLIENT_SECRET(self) -> str:
        return os.getenv("APS_CLIENT_SECRET", "")

    @property
    def APS_SERVICE_PORT(self) -> int:
        return int(os.getenv("APS_SERVICE_PORT", "3001"))

    @property
    def APS_CALLBACK_URL(self) -> str:
        return os.getenv("APS_CALLBACK_URL", "")

    # ── BaseX (XML Database) ─────────────────────────────────────────────
    @property
    def BASEX_HOST(self) -> str:
        return os.getenv("BASEX_HOST", "localhost")

    @property
    def BASEX_PORT(self) -> int:
        return int(os.getenv("BASEX_PORT", "1984"))

    @property
    def BASEX_USER(self) -> str:
        return os.getenv("BASEX_USER", "admin")

    @property
    def BASEX_PASSWORD(self) -> str:
        return os.getenv("BASEX_PASSWORD", "")

    @property
    def BASEX_DB_NAME(self) -> str:
        return os.getenv("BASEX_DB_NAME", "bsdd_documents")

    # ── OpenSearch (Vector Memory) ────────────────────────────────────────
    @property
    def OPENSEARCH_HOST(self) -> str:
        return os.getenv("OPENSEARCH_HOST", "localhost")

    @property
    def OPENSEARCH_PORT(self) -> int:
        return int(os.getenv("OPENSEARCH_PORT", "9200"))

    @property
    def OPENSEARCH_USER(self) -> str:
        return os.getenv("OPENSEARCH_USER", "admin")

    @property
    def OPENSEARCH_PASSWORD(self) -> str:
        return os.getenv("OPENSEARCH_PASSWORD", "")

    # ── Redis ─────────────────────────────────────────────────────────────
    @property
    def REDIS_URL(self) -> str:
        return os.getenv("REDIS_URL", "")

    # ── API Security ──────────────────────────────────────────────────────
    @property
    def API_KEY(self) -> str:
        """Optional API key for protecting admin endpoints.
        When empty, admin endpoints are unprotected (dev mode)."""
        return os.getenv("API_KEY", "")

    @property
    def CORS_METHODS(self) -> List[str]:
        """Allowed HTTP methods for CORS. Defaults to safe set."""
        return _csv("CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS")

    @property
    def CORS_HEADERS(self) -> List[str]:
        """Allowed HTTP headers for CORS. Defaults to common set."""
        return _csv("CORS_HEADERS",
                     "Content-Type,Authorization,X-API-Key,Accept")

    # ── Frontend ──────────────────────────────────────────────────────────
    @property
    def FRONTEND_PORT(self) -> int:
        return int(os.getenv("FRONTEND_PORT", "5173"))

    def __repr__(self) -> str:
        return "<BIMTwinOps Config>"


# Module-level singleton
cfg = _Config()
