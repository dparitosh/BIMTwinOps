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

try:
    from .planning_agent import planning_agent_node as _planning_agent_node
except ImportError:  # pragma: no cover
    async def _planning_agent_node(state: "AgentState") -> "AgentState":
        """Planning Agent placeholder (used when planning_agent.py is unavailable)."""
        logger.info("Planning Agent: Using placeholder")
        msgs = list(state.get("messages", []))
        return {
            **state,
            "messages": msgs + [
                AIMessage(content="[Planning Agent] Placeholder - Planning agent module not available")
            ],
            "next": END,
        }

try:
    from .executor_agent import ExecutorAgent
    _executor_agent = ExecutorAgent()
except ImportError:  # pragma: no cover
    _executor_agent = None

# Bind names used by the graph
query_agent_node = _query_agent_node
action_agent_node = _action_agent_node
planning_agent_node = _planning_agent_node


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
# Topic Guardrails (Lightweight - no NeMo dependency)
# ============================================================================

# BIM/Construction domain keywords for topic validation
BIM_DOMAIN_KEYWORDS = {
    # IFC Entity types
    "ifc", "wall", "door", "window", "slab", "beam", "column", "stair", "roof",
    "space", "zone", "building", "storey", "floor", "element", "site", "project",
    # Point cloud
    "point cloud", "pointcloud", "segment", "segmentation", "scan", "lidar", "3d",
    # BIM concepts
    "bim", "model", "geometry", "property", "classification", "bsdd", "ifc4",
    "pset", "property set", "quantity", "material", "fire rating", "thermal",
    # Spatial
    "spatial", "location", "coordinates", "bounds", "near", "adjacent", "contains",
    # Building systems
    "hvac", "mep", "plumbing", "electrical", "structural", "architectural",
    "duct", "pipe", "cable", "conduit", "equipment",
    # Analysis
    "compliance", "validation", "clash", "interference", "energy", "acoustic",
    # Document types
    "ifc file", "revit", "cad", "dwg", "rvt", "nwd",
}

# Off-topic / dangerous patterns to reject
OFF_TOPIC_PATTERNS = [
    r"\b(hack|exploit|bypass|inject|overflow)\b",
    r"\b(password|credential|api.?key|secret)\b",
    r"\b(porn|nude|xxx|nsfw)\b",
    r"\b(weapon|bomb|explosive|drug)\b",
    r"\b(stock|invest|crypto|bitcoin|forex)\b",
    r"\b(medical|diagnos|prescri|symptom|disease)\b",
    r"\b(legal|lawsuit|attorney|sue)\b",
]


def _check_topic_guardrails(user_input: str) -> tuple[bool, str]:
    """Check if user input is within BIM/construction domain.

    Returns:
        Tuple of (is_valid, reason)
        - is_valid: True if on-topic and safe
        - reason: Explanation of why blocked (if blocked)
    """
    text = (user_input or "").strip().lower()

    # Check for off-topic/dangerous patterns first
    for pattern in OFF_TOPIC_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "Request appears to be off-topic or contains restricted content."

    # Check if any BIM domain keywords present
    has_domain_keyword = any(kw in text for kw in BIM_DOMAIN_KEYWORDS)

    # Allow generic questions about the system itself
    system_meta_patterns = [
        r"\b(help|assist|what can|how do|capabilities)\b",
        r"\b(hello|hi|hey|thanks|thank you)\b",
    ]
    is_system_meta = any(re.search(p, text) for p in system_meta_patterns)

    if has_domain_keyword or is_system_meta:
        return True, "On-topic: BIM/construction domain or system interaction."

    # Short inputs (< 10 chars) are ambiguous, allow them
    if len(text) < 10:
        return True, "Input too short to classify; allowing."

    return False, (
        "Request does not appear to be related to BIM, building information, "
        "or construction data. Please ask about IFC models, point clouds, "
        "building elements, or spatial queries."
    )


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
        # Step 1: Topic guardrails check
        is_on_topic, guardrail_reason = _check_topic_guardrails(user_input)
        
        if not is_on_topic:
            logger.warning("Router: Topic guardrail blocked request - %s", guardrail_reason)
            return {
                **state,
                "intent": "blocked",
                "router_reasoning": f"Guardrail: {guardrail_reason}",
                "messages": messages + [
                    AIMessage(content=(
                        f"I can only help with BIM and construction-related queries. {guardrail_reason}\n\n"
                        "Examples of things I can help with:\n"
                        "- 'Show all walls with fire rating > 60 minutes'\n"
                        "- 'Find spaces on Floor 2'\n"
                        "- 'Upload IFC file for analysis'\n"
                        "- 'Segment this point cloud'"
                    ))
                ],
                "next": END,
            }
        
        # Step 2: Classify intent
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
# Executor Agent Node (for HITL execution)
# ============================================================================

async def executor_agent_node(state: AgentState) -> AgentState:
    """
    Executor Agent: Execute approved action plans

    This node is invoked after HITL approval to execute pending actions.
    It receives the approved action plan from state metadata and executes it.

    Args:
        state: Current agent state with approved action plan

    Returns:
        Updated state with execution results
    """
    logger.info("Executor Agent: Executing approved action")

    if _executor_agent is None:
        return {
            **state,
            "messages": list(state.get("messages", [])) + [
                AIMessage(content="[Executor] Error: Executor agent not available")
            ],
            "error": "Executor agent not available",
            "next": END,
        }

    metadata = state.get("metadata", {}) or {}
    action_plan = metadata.get("action_plan")

    if not action_plan:
        return {
            **state,
            "messages": list(state.get("messages", [])) + [
                AIMessage(content="[Executor] No action plan found in state to execute")
            ],
            "next": END,
        }

    try:
        results = await _executor_agent.execute(action_plan, metadata=metadata)

        response = f"Action executed successfully. Results: {len(results)} operation(s) completed."
        return {
            **state,
            "mcp_results": results,
            "messages": list(state.get("messages", [])) + [
                AIMessage(content=response)
            ],
            "next": END,
        }

    except Exception as e:  # pylint: disable=broad-except
        logger.exception("Executor agent error")
        return {
            **state,
            "error": str(e),
            "messages": list(state.get("messages", [])) + [
                AIMessage(content=f"[Executor] Execution failed: {str(e)}")
            ],
            "next": "error_handler",
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
        START → Router → [Query|Action|Planning|Executor|Unknown] → END
                              ↓
                         (HITL approval flow)
                              ↓
                         Executor → END
    
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
    graph.add_node("executor_agent", executor_agent_node)
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
            "executor_agent": "executor_agent",
            "unknown_agent": "unknown_agent",
            "error_handler": "error_handler"
        }
    )
    
    # Action agent can route to executor (after HITL) or END
    def route_from_action(state: AgentState) -> str:
        """Route from action agent - may go to executor or end"""
        next_node = state.get("next", END)
        # If requires approval, action agent returns END (wait for HITL)
        # If no approval needed and already executed, also END
        if next_node == "executor_agent":
            return "executor_agent"
        return END
    
    graph.add_conditional_edges(
        "action_agent",
        route_from_action,
        {
            "executor_agent": "executor_agent",
            END: END
        }
    )
    
    # Other specialist agents route to END
    graph.add_edge("query_agent", END)
    graph.add_edge("planning_agent", END)
    graph.add_edge("executor_agent", END)
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

    async def execute_approved_action(
        self,
        action_plan: Dict[str, Any],
        thread_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute an approved action plan directly (post-HITL)
        
        This method bypasses the router and directly invokes the executor
        for actions that have already been approved via HITL.
        
        Args:
            action_plan: The approved action plan to execute
            thread_id: Conversation thread ID for checkpointing
            metadata: Additional context (user_id, approved_by, etc.)
        
        Returns:
            Dict with execution results
        """
        logger.info("Executing approved action: %s", action_plan.get("action_type"))
        
        # Build state with approved action plan
        initial_state: AgentState = {
            "messages": [HumanMessage(content=f"Execute approved action: {action_plan.get('action_type')}")],
            "user_input": f"[HITL-APPROVED] Execute {action_plan.get('action_type')}",
            "intent": "executor",
            "metadata": {
                **(metadata or {}),
                "action_plan": action_plan,
                "timestamp": datetime.now().isoformat(),
                "thread_id": thread_id,
                "hitl_approved": True
            },
            "next": "executor_agent"  # Skip router, go directly to executor
        }
        
        # Create a minimal graph that just runs the executor
        try:
            # Run executor directly
            result_state = await executor_agent_node(initial_state)
            
            messages = result_state.get("messages", [])
            response = messages[-1].content if messages else "Execution completed"
            
            return {
                "response": response,
                "success": "error" not in result_state,
                "mcp_results": result_state.get("mcp_results", []),
                "thread_id": thread_id
            }
            
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Execute approved action error")
            return {
                "response": f"Execution failed: {str(e)}",
                "success": False,
                "thread_id": thread_id
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
