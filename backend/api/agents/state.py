"""Shared agent state types.

This module exists to avoid circular imports between the orchestrator and
specialist agents.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, TypedDict
from typing_extensions import NotRequired

try:
    from langchain_core.messages import BaseMessage
except Exception:  # pragma: no cover
    BaseMessage = Any  # type: ignore


class AgentState(TypedDict):
    """Shared state passed between agent nodes."""

    # Core conversation state
    messages: Sequence[BaseMessage]
    user_input: str

    # Routing & intent
    intent: NotRequired[str]  # "query" | "action" | "planning" | "unknown"
    router_reasoning: NotRequired[str]
    current_agent: NotRequired[str]

    # MCP tool execution
    mcp_results: NotRequired[List[Dict[str, Any]]]

    # Error handling
    error: NotRequired[str]

    # Context & metadata
    metadata: NotRequired[Dict[str, Any]]

    # Control flow
    next: NotRequired[str]
