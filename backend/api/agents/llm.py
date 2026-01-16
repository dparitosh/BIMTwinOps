"""LLM client(s) for SMART_BIM.

This module intentionally avoids optional LangChain provider packages
(corporate-friendly). Instead, it provides small
dedicated clients:

- Ollama: direct HTTP calls to the local Ollama server.
- Azure OpenAI: via the official `openai` Python SDK (AzureOpenAI).

The returned client implements a minimal chat interface:

- invoke(input) -> response (has `.content`)
- ainvoke(input) -> response (async)

Kept separate from `agent_orchestrator.py` to avoid circular imports.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Iterable

import asyncio
import requests  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


class ChatResponse:
    """Minimal response wrapper to mimic `response.content` used in agents."""

    def __init__(self, content: str):
        self.content = content


def _coerce_messages_to_text(messages: Any) -> str:
    """Convert a chat input into plain text.

    Supports:
    - a string
    - an iterable of LangChain BaseMessage (has `.content`)
    - an iterable of dict messages like {"type": "human"|"ai", "content": "..."}
    """

    if isinstance(messages, str):
        return messages

    if isinstance(messages, dict):
        # Single message dict
        return str(messages.get("content") or "")

    if isinstance(messages, Iterable):
        parts: list[str] = []
        for m in messages:
            if isinstance(m, str):
                parts.append(m)
            elif isinstance(m, dict):
                role = m.get("type") or m.get("role") or "message"
                parts.append(f"{role}: {m.get('content', '')}")
            else:
                content = getattr(m, "content", None)
                if content is not None:
                    parts.append(str(content))
                else:
                    parts.append(str(m))
        return "\n".join([p for p in parts if p.strip()])

    return str(messages)


class OllamaClient:
    def __init__(self, *, base_url: str, model: str, temperature: float):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = float(temperature)

    def invoke(self, messages: Any) -> ChatResponse:
        prompt = _coerce_messages_to_text(messages)
        url = f"{self.base_url}/api/generate"

        resp = requests.post(
            url,
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": self.temperature},
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return ChatResponse(content=str(data.get("response", "")))

    async def ainvoke(self, messages: Any) -> ChatResponse:
        return await asyncio.to_thread(self.invoke, messages)


class AzureOpenAIClient:
    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        deployment_name: str,
        api_version: str,
        temperature: float,
    ):
        self.endpoint = endpoint
        self.api_key = api_key
        self.deployment_name = deployment_name
        self.api_version = api_version
        self.temperature = float(temperature)

        try:
            from openai import AzureOpenAI  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("openai package is required for Azure LLM") from e

        self._client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
        )

    def invoke(self, messages: Any) -> ChatResponse:
        text = _coerce_messages_to_text(messages)

        # Use a simple chat format
        result = self._client.chat.completions.create(
            model=self.deployment_name,
            messages=[{"role": "user", "content": text}],
            temperature=self.temperature,
        )
        content = result.choices[0].message.content if result.choices else ""
        return ChatResponse(content=content or "")

    async def ainvoke(self, messages: Any) -> ChatResponse:
        # Avoid requiring AsyncAzureOpenAI; thread off sync call.
        return await asyncio.to_thread(self.invoke, messages)


def create_llm(*, temperature: float = 0.7, model: str = "gpt-4o") -> Any:
    """Create an LLM client.

    Controlled by env var `LLM_PROVIDER` ("ollama" or "azure").
    """

    llm_provider = os.getenv("LLM_PROVIDER", "ollama").lower().strip()

    if llm_provider == "ollama":
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
        logger.info("Using Ollama LLM: %s at %s", ollama_model, ollama_url)
        return OllamaClient(base_url=ollama_url, model=ollama_model, temperature=temperature)

    # Azure OpenAI
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", os.getenv("AZURE_OPENAI_DEPLOYMENT", model))
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

    if not endpoint or not api_key:
        raise RuntimeError("LLM_PROVIDER=azure requires AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY")

    logger.info("Using Azure OpenAI deployment: %s", deployment)
    return AzureOpenAIClient(
        endpoint=endpoint,
        api_key=api_key,
        deployment_name=deployment,
        api_version=api_version,
        temperature=temperature,
    )
