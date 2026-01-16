"""
LangGraph Agent Orchestrator
State machine for coordinating AI agents and MCP tools.

This module implements the central orchestration logic for the 2026
Intelligent App architecture, following ADR-002.

Key Principles:
1. Reasoning ≠ Execution: Agents reason, MCP tools execute
2. State Persistence: Redis-backed checkpointing
3. Routing: Intent-based agent selection
4. Memory: OpenSearch hybrid retrieval

Components:
- AgentState: Shared state schema
- Router Agent: Intent classification & routing
- Specialist Agents: Domain-specific reasoning
- MCP Integration: Tool execution via MCP Host

Architecture:
    User Input
        ↓
    Router Agent (classify intent)
        ↓
    ┌───────────────┬───────────────┬───────────────┐
    │  Query Agent  │ Action Agent  │ Planning Agent│
    └───────────────┴───────────────┴───────────────┘
        ↓               ↓               ↓
    MCP Host → Neo4j / BaseX / bSDD Servers

References:
- LangGraph: https://github.com/langchain-ai/langgraph
- Redis Checkpointer: https://langchain-ai.github.io/langgraph/reference/checkpoints/
"""

from typing import TypedDict, Annotated, Sequence, Dict, Any, Optional, List
from typing_extensions import NotRequired
import operator
from datetime import datetime
import os
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LangGraph imports
from langgraph.graph import StateGraph, END
try:
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:  # pragma: no cover
    from langgraph.checkpoint import MemorySaver  # type: ignore

# LangChain imports
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# Redis checkpointer (optional, fallback to memory)
try:
    from langgraph.checkpoint.redis import RedisSaver  # type: ignore[import-not-found]
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis checkpointer not available, using memory")

# Security layer integration
from ..security.security_layer import SecurityLayer

# Specialist agents (optional)
SPECIALIST_AGENTS_AVAILABLE = True
try:
    from .query_agent import query_agent_node as _query_agent_node
except ImportError:  # pragma: no cover
    SPECIALIST_AGENTS_AVAILABLE = False

    async def _query_agent_node(state: "AgentState") -> "AgentState":
        """Query Agent placeholder (used when specialist agents are unavailable)."""
        logger.info("Query Agent: Using placeholder (specialist agents not loaded)")
        msgs = list(state.get("messages", []))
        return {
            **state,
            "messages": msgs + [
                AIMessage(content="[Query Agent] Placeholder - Specialist agents module not available")
            ],
            "next": END,
        }

try:
    from .action_agent import action_agent_node as _action_agent_node
except ImportError:  # pragma: no cover
    SPECIALIST_AGENTS_AVAILABLE = False

    async def _action_agent_node(state: "AgentState") -> "AgentState":
        """Action Agent placeholder (used when specialist agents are unavailable)."""
        logger.info("Action Agent: Using placeholder (specialist agents not loaded)")
        msgs = list(state.get("messages", []))
        return {
            **state,
            "messages": msgs + [
                AIMessage(content="[Action Agent] Placeholder - Specialist agents module not available")
            ],
            "next": END,
        }

# Bind names used by the graph
query_agent_node = _query_agent_node
action_agent_node = _action_agent_node


# ============================================================================
# State Schema
# ============================================================================

class AgentState(TypedDict):
    """
    Shared state for all agents in the orchestration graph
    
    This state is passed between nodes and persisted in checkpoints.
    Following functional core principles: state is immutable, updates
    create new versions.
    
    Fields:
        messages: Conversation history (LangChain message format)
        user_input: Current user request
        intent: Classified intent (query/action/planning/unknown)
        router_reasoning: Router agent's classification reasoning
        current_agent: Active specialist agent
        mcp_results: Results from MCP tool calls
        error: Error message if any
        metadata: Additional context (user_id, session_id, timestamps)
        next: Next node to execute (routing control)
    """
    # Core conversation state
    messages: Annotated[Sequence[BaseMessage], operator.add]
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


def _classify_intent(user_input: str) -> tuple[str, str]:
    """Deterministic intent classifier.

    Corporate-friendly: avoids extra LLM provider dependencies and gives predictable routing.
    """

    text = (user_input or "").strip().lower()

    # Planning: explicit multi-step intent
    if any(k in text for k in ["then ", "after ", "steps", "plan", "workflow", "sequence", "schedule"]):
        return "planning", "Detected planning keywords (multi-step/workflow language)."

    # Action: destructive or modifying
    if re.search(r"\b(delete|remove|drop)\b", text):
        return "action", "Detected destructive action keywords (delete/remove/drop)."
    if re.search(r"\b(create|add|insert|update|modify|change|edit|set|upload|store|save|import|segment|classify)\b", text):
        return "action", "Detected state-modifying keywords (create/update/upload/segment/etc.)."

    # Query: informational
    if re.search(r"\b(show|list|find|search|get|retrieve|what|which|who|where|how many|count|definition)\b", text):
        return "query", "Detected read-only query keywords (show/find/get/definition/etc.)."

    return "unknown", "No clear intent keywords found; needs clarification."


# ============================================================================
# Router Agent
# ============================================================================

async def router_agent_node(state: AgentState) -> AgentState:
    """
    Router Agent: Classify user intent and route to specialist agent
    
    Analyzes user input to determine:
    - Query: Information retrieval (read-only)
    - Action: State modification (write operations)
    - Planning: Multi-step workflows
    - Unknown: Unclear intent (fallback)
    
    Uses chain-of-thought reasoning to explain classification.
    
    Args:
        state: Current agent state
    
    Returns:
        Updated state with intent classification and routing decision
    """
    logger.info("Router Agent: Analyzing user intent")
    
    user_input = state["user_input"]
    messages = list(state.get("messages", []))
    
    try:
        intent, reasoning = _classify_intent(user_input)
        logger.info("Router classified intent: %s - %s", intent, reasoning)
        
        # Update state with routing decision
        return {
            **state,
            "intent": intent,
            "router_reasoning": reasoning,
            "messages": messages + [
                AIMessage(content=f"[Router] Intent: {intent} - {reasoning}")
            ],
            "next": f"{intent}_agent"  # Route to specialist agent
        }
        
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("Router agent error")
        return {
            **state,
            "intent": "unknown",
            "error": f"Router failed: {str(e)}",
            "next": "error_handler"
        }


 


# ============================================================================
# Planning Agent (Placeholder)
# ============================================================================

async def planning_agent_node(state: AgentState) -> AgentState:
    """
    Planning Agent: Handle multi-step workflows
    
    Responsibilities:
    - Break down complex tasks
    - Create execution plans
    - Coordinate specialist agents
    - Track progress
    
    Uses task decomposition and recursive planning.
    
    Args:
        state: Current agent state
    
    Returns:
        Updated state with plan and execution steps
    """
    logger.info("Planning Agent: Creating execution plan")
    
    # Planning logic not implemented yet.
    
    return {
        **state,
        "messages": list(state.get("messages", [])) + [
            AIMessage(content="[Planning Agent] Placeholder - Implementation pending")
        ],
        "next": END
    }


# ============================================================================
# Unknown Handler
# ============================================================================

async def unknown_handler_node(state: AgentState) -> AgentState:
    """
    Unknown Handler: Clarification requests for ambiguous intents
    
    Asks user for more information to clarify intent.
    
    Args:
        state: Current agent state
    
    Returns:
        Updated state with clarification request
    """
    logger.info("Unknown Handler: Requesting clarification")
    
    clarification = (
        "I couldn't determine how to help with that request. "
        "Could you please clarify? For example:\n\n"
        "- **Query**: 'Show me all walls with fire rating > 60'\n"
        "- **Action**: 'Create a new space named Conference Room A'\n"
        "- **Planning**: 'Generate a compliance report for Fire Safety'\n\n"
        "What would you like to do?"
    )
    
    return {
        **state,
        "messages": list(state.get("messages", [])) + [
            AIMessage(content=clarification)
        ],
        "next": END
    }


# ============================================================================
# Error Handler
# ============================================================================

async def error_handler_node(state: AgentState) -> AgentState:
    """
    Error Handler: Graceful error recovery
    
    Logs errors and returns user-friendly message.
    
    Args:
        state: Current agent state with error field
    
    Returns:
        Updated state with error message
    """
    error_msg = state.get("error", "Unknown error occurred")
    logger.error("Error Handler: %s", error_msg)
    
    return {
        **state,
        "messages": list(state.get("messages", [])) + [
            AIMessage(content=f"An error occurred: {error_msg}")
        ],
        "next": END
    }


# ============================================================================
# Graph Construction
# ============================================================================

def create_agent_graph() -> Any:
    """
    Create LangGraph state machine for agent orchestration
    
    Graph structure:
        START → Router → [Query|Action|Planning|Unknown] → END
    
    Checkpointing:
        - Redis if available (production)
        - Memory otherwise (development)
    
    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Creating agent orchestration graph")
    
    # Create graph with AgentState schema
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("router", router_agent_node)
    graph.add_node("query_agent", query_agent_node)
    graph.add_node("action_agent", action_agent_node)
    graph.add_node("planning_agent", planning_agent_node)
    graph.add_node("unknown_agent", unknown_handler_node)
    graph.add_node("error_handler", error_handler_node)
    
    # Define edges (routing logic)
    graph.set_entry_point("router")
    
    # Router routes to specialist agents based on intent
    def route_from_router(state: AgentState) -> str:
        """Route based on router's decision"""
        next_node = state.get("next", "unknown_agent")
        logger.info("Routing to: %s", next_node)
        return next_node
    
    graph.add_conditional_edges(
        "router",
        route_from_router,
        {
            "query_agent": "query_agent",
            "action_agent": "action_agent",
            "planning_agent": "planning_agent",
            "unknown_agent": "unknown_agent",
            "error_handler": "error_handler"
        }
    )
    
    # All specialist agents route to END
    graph.add_edge("query_agent", END)
    graph.add_edge("action_agent", END)
    graph.add_edge("planning_agent", END)
    graph.add_edge("unknown_agent", END)
    graph.add_edge("error_handler", END)
    
    # Configure checkpointer
    if REDIS_AVAILABLE and os.getenv("REDIS_URL"):
        logger.info("Using Redis checkpointer")
        checkpointer = RedisSaver(os.getenv("REDIS_URL"))
    else:
        logger.info("Using memory checkpointer")
        checkpointer = MemorySaver()
    
    # Compile graph
    compiled_graph = graph.compile(checkpointer=checkpointer)
    
    logger.info("Agent graph created successfully")
    return compiled_graph


# ============================================================================
# Public API
# ============================================================================

class AgentOrchestrator:
    """
    Main orchestrator for agent interactions
    
    Provides high-level API for:
    - Processing user requests
    - Managing conversation state
    - Accessing MCP tools
    
    Usage:
        orchestrator = AgentOrchestrator()
        response = await orchestrator.process("Show me all walls")
    """
    
    def __init__(self):
        """Initialize orchestrator with graph and MCP host"""
        self.graph = create_agent_graph()
        # MCP host is created asynchronously by specialist agents when needed.
        self.mcp_host = None
        self.security = SecurityLayer()
        logger.info("AgentOrchestrator initialized")
    
    async def process(
        self,
        user_input: str,
        thread_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process user input through agent graph
        
        Args:
            user_input: User's request
            thread_id: Conversation thread ID for checkpointing
            metadata: Additional context (user_id, etc.)
        
        Returns:
            Dict with response, intent, and execution trace
        """
        logger.info("Processing request: %s...", user_input[:100])
        
        # Security validation
        validation_result = self.security.validate_and_log(
            user_input=user_input,
            user_id=metadata.get("user_id") if metadata else None,
            session_id=thread_id
        )
        
        if not validation_result.is_valid:
            logger.warning("Input validation failed: %s", validation_result.errors)
            return {
                "response": f"Input validation failed: {', '.join(validation_result.errors)}",
                "intent": "error",
                "thread_id": thread_id,
                "success": False,
                "validation_errors": validation_result.errors
            }
        
        # Use sanitized input
        sanitized_input = validation_result.sanitized_input or user_input
        
        # Initialize state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=sanitized_input)],
            "user_input": sanitized_input,
            "metadata": metadata or {
                "timestamp": datetime.now().isoformat(),
                "thread_id": thread_id
            }
        }
        
        # Run graph
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            final_state = await self.graph.ainvoke(initial_state, config)
            
            # Extract response
            messages = final_state.get("messages", [])
            response = messages[-1].content if messages else "No response generated"
            
            return {
                "response": response,
                "intent": final_state.get("intent", "unknown"),
                "thread_id": thread_id,
                "success": "error" not in final_state,
                "state_metadata": final_state.get("metadata", {}),
                "trace": {
                    "router_reasoning": final_state.get("router_reasoning"),
                    "current_agent": final_state.get("current_agent"),
                    "mcp_results": final_state.get("mcp_results", [])
                }
            }
            
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Orchestrator error")
            return {
                "response": f"An error occurred: {str(e)}",
                "intent": "error",
                "thread_id": thread_id,
                "success": False
            }


# ============================================================================
# Testing & Development
# ============================================================================

async def test_orchestrator():
    """Test orchestrator with sample queries"""
    orchestrator = AgentOrchestrator()
    
    test_queries = [
        "Show me all walls in the model",
        "Create a new space named Conference Room A",
        "Generate a compliance report",
        "What's the weather like?"  # Out of scope
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        result = await orchestrator.process(query)
        
        print(f"Intent: {result['intent']}")
        print(f"Response: {result['response']}")
        print(f"Success: {result['success']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_orchestrator())
