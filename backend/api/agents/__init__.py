"""
Agents Package
Specialist agents for BIM/AEC intelligent workflows.

Components:
- Query Agent: Read-only information retrieval
- Action Agent: State modification operations
- Planning Agent: Multi-step coordination (coming soon)

Note: Agent Orchestrator imports separately to avoid LangGraph dependency issues.
"""

__version__ = "0.1.0"

# Don't import orchestrator here to avoid langgraph issues
# from .agent_orchestrator import AgentOrchestrator, AgentState, create_agent_graph

__all__ = []
