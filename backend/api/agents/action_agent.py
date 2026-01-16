"""
Action Agent: State Modification Operations
Specialist agent for write operations and data mutations.

This agent handles all state-modifying operations:
1. Neo4j graph modifications (create, update, delete)
2. Document storage in BaseX
3. Point cloud segmentation triggers
4. Audit logging for all mutations

Architecture:
    User Action → Router → Action Agent
        ↓
    [Validate & Authorize] → Security Layer
        ↓
    [Neo4j | BaseX | PointCloud] via MCP
        ↓
    Audit Log → Confirmation → UI Generator

Tools Available:
- create_nodes (Neo4j): Create graph nodes
- create_relationships (Neo4j): Create edges
- update_properties (Neo4j): Modify node properties
- store_document (BaseX): Store IFC/XML documents
- online_segmentation (PointCloud): Trigger segmentation

Safety Features:
- Pre-execution validation
- Transaction rollback on error
- Comprehensive audit logging
- User confirmation for destructive operations
"""

from typing import Any, Dict, List
import logging
from datetime import datetime
import re

from .state import AgentState

from ..approvals.store import get_pending_action_store
from .executor_agent import ExecutorAgent

LANGCHAIN_AVAILABLE = False
LC_AIMessage: Any = None
LC_HumanMessage: Any = None

try:
    from langchain_core.messages import AIMessage as LC_AIMessage, HumanMessage as LC_HumanMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


def make_ai_message(content: str) -> Any:
    if LANGCHAIN_AVAILABLE and LC_AIMessage is not None:
        return LC_AIMessage(content=content)
    return {"type": "ai", "content": content}


def make_human_message(content: str) -> Any:
    if LANGCHAIN_AVAILABLE and LC_HumanMessage is not None:
        return LC_HumanMessage(content=content)
    return {"type": "human", "content": content}

# Security layer (optional)
try:
    from ..security.security_layer import SecurityLayer as SecurityLayerCls, AuditLogger as AuditLoggerCls
except ImportError:  # pragma: no cover
    SecurityLayerCls = None  # type: ignore
    AuditLoggerCls = None  # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Action Agent
# ============================================================================

class ActionAgent:
    """
    Action Agent for state modification operations
    
    Handles:
    - Neo4j write operations (create, update, delete)
    - Document storage (IFC files, XML)
    - Point cloud segmentation triggers
    - Audit logging
    
    Safety:
    - Validates all inputs via security layer
    - Logs all mutations
    - Supports transaction rollback
    - Requires user confirmation for destructive ops
    
    Usage:
        agent = ActionAgent()
        result = await agent.process(state)
    """
    
    def __init__(self):
        """Initialize action agent"""
        self.security = SecurityLayerCls() if SecurityLayerCls is not None else None
        self.audit_logger = AuditLoggerCls() if AuditLoggerCls is not None else None

        self.pending_store = get_pending_action_store()
        self.executor = ExecutorAgent()

        logger.info("ActionAgent initialized")
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Process action request
        
        Args:
            state: Current agent state
        
        Returns:
            Updated state with action results
        """
        logger.info("Action Agent: Processing state modification")

        user_input = state["user_input"]
        messages = list(state.get("messages", []))
        
        try:
            # Step 1: Validate action (already done by orchestrator, but double-check)
            if self.security:
                validation = self.security.validate_and_log(
                    user_input=user_input,
                    user_id=state.get("metadata", {}).get("user_id"),
                    session_id=state.get("metadata", {}).get("session_id")
                )
                
                if not validation.is_valid:
                    return {
                        **state,
                        "error": "Action validation failed",
                        "messages": messages + [
                            make_ai_message(content=f"Action blocked: {', '.join(validation.errors)}")
                        ],
                        "next": "error_handler"
                    }
            
            # Step 2: Plan action execution
            action_plan = await self._plan_action(user_input)
            
            # Step 3: Check if confirmation needed
            if action_plan.get("requires_confirmation", False):
                # HITL: create a pending approval item and do NOT execute yet
                logger.info("Action requires confirmation (queued): %s", action_plan.get("action_type"))

                meta = state.get("metadata", {}) or {}
                pending = self.pending_store.create(
                    action_plan,
                    user_id=meta.get("user_id"),
                    session_id=meta.get("session_id"),
                    thread_id=meta.get("thread_id"),
                )

                if self.audit_logger:
                    self.audit_logger.log_agent_action(
                        agent_name="action_agent",
                        action="pending_action_created",
                        intent="state_modification",
                        result="success",
                        user_id=meta.get("user_id"),
                        session_id=meta.get("session_id"),
                    )

                response = (
                    "This action requires approval before it can be executed. "
                    f"Pending action id: {pending.id}. "
                    "Approve via POST /api/approvals/{id}/approve or reject via POST /api/approvals/{id}/reject."
                )

                return {
                    **state,
                    "messages": messages + [make_ai_message(content=response)],
                    "metadata": {
                        **meta,
                        "action_plan": action_plan,
                        "pending_action_id": pending.id,
                        "requires_approval": True,
                    },
                    "next": "END",
                }

            # Step 4: Execute action (via executor)
            results = await self.executor.execute(
                action_plan,
                metadata={
                    "user_id": state.get("metadata", {}).get("user_id"),
                    "session_id": state.get("metadata", {}).get("session_id"),
                    "thread_id": state.get("metadata", {}).get("thread_id"),
                },
            )
            
            # Step 5: Log to audit trail
            if self.audit_logger:
                self.audit_logger.log_agent_action(
                    agent_name="action_agent",
                    action=action_plan["action_type"],
                    intent="state_modification",
                    result="success",
                    user_id=state.get("metadata", {}).get("user_id"),
                    session_id=state.get("metadata", {}).get("session_id")
                )
            
            # Step 6: Generate response
            response = self._generate_response(action_plan, results)
            
            return {
                **state,
                "messages": messages + [make_ai_message(content=response)],
                "mcp_results": results,
                "metadata": {
                    **state.get("metadata", {}),
                    "action_plan": action_plan,
                    "actions_performed": len(results)
                },
                "next": "END"
            }
        
        except (RuntimeError, ValueError, TypeError) as e:
            logger.error("Action Agent error: %s", str(e))
            
            # Log failure
            if self.audit_logger:
                self.audit_logger.log_agent_action(
                    agent_name="action_agent",
                    action="action_failed",
                    intent="state_modification",
                    result="error",
                    user_id=state.get("metadata", {}).get("user_id"),
                    session_id=state.get("metadata", {}).get("session_id")
                )
            
            return {
                **state,
                "error": str(e),
                "messages": messages + [
                    make_ai_message(content=f"Action failed: {str(e)}")
                ],
                "next": "error_handler"
            }
    
    async def _plan_action(self, user_input: str) -> Dict[str, Any]:
        """
        Plan action execution
        
        Args:
            user_input: User's action request
        
        Returns:
            Action execution plan
        """
        # Simple keyword-based planning
        query_lower = user_input.lower()

        # Heuristic bulk estimation (used for HITL thresholds)
        bulk_estimate = self._estimate_bulk_count(query_lower)
        warnings: List[str] = []
        
        # Determine action type
        if any(word in query_lower for word in ["create", "add", "new", "insert"]):
            if "relationship" in query_lower or "connect" in query_lower:
                action_type = "create_relationship"
                tool = "create_relationships"
            else:
                action_type = "create_node"
                tool = "create_nodes"
            requires_confirmation = False
        
        elif any(word in query_lower for word in ["update", "modify", "change", "edit", "set"]):
            action_type = "update_properties"
            tool = "update_properties"
            requires_confirmation = False
        
        elif any(word in query_lower for word in ["delete", "remove", "drop"]):
            action_type = "delete"
            tool = "delete_nodes"
            requires_confirmation = True  # Destructive operation
        
        elif any(word in query_lower for word in ["store", "save", "upload", "document"]):
            action_type = "store_document"
            tool = "store_document"
            requires_confirmation = False
        
        elif any(word in query_lower for word in ["segment", "classify", "analyze point"]):
            action_type = "segment_pointcloud"
            tool = "online_segmentation"
            requires_confirmation = False
        
        else:
            # Default to property update
            action_type = "update_properties"
            tool = "update_properties"
            requires_confirmation = False

        # HITL thresholds
        # - DELETE: mandatory (already true)
        # - BULK_UPDATE > 5: mandatory
        # - CREATE > 10: warning only
        if action_type == "update_properties" and bulk_estimate is not None and bulk_estimate > 5:
            requires_confirmation = True

        if action_type == "create_node" and bulk_estimate is not None and bulk_estimate > 10:
            warnings.append(
                f"Large create detected (estimated {bulk_estimate} items). Consider running in smaller batches."
            )
        
        plan = {
            "action_type": action_type,
            "tool": tool,
            "requires_confirmation": requires_confirmation,
            "parameters": self._extract_parameters(user_input, action_type),
            "bulk_estimate": bulk_estimate,
            "warnings": warnings,
        }
        
        logger.info("Action plan: %s via %s", action_type, tool)
        return plan

    def _estimate_bulk_count(self, query_lower: str) -> int | None:
        """Best-effort estimate of how many items an action might affect.

        This is intentionally conservative and heuristic-based.
        """

        if any(w in query_lower for w in ["all ", "every ", "entire ", "bulk "]):
            # Treat as bulk if user indicates global scope.
            return 999

        # Patterns like "create 12", "update 6", "delete 3"
        m = re.search(r"\b(?:create|add|insert|update|modify|change|delete|remove)\s+(\d{1,4})\b", query_lower)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return None

        # Patterns like "12 items", "7 nodes", "20 elements"
        m2 = re.search(r"\b(\d{1,4})\s+(?:items?|nodes?|elements?|segments?)\b", query_lower)
        if m2:
            try:
                return int(m2.group(1))
            except ValueError:
                return None

        return None
    
    def _extract_parameters(self, user_input: str, action_type: str) -> Dict[str, Any]:
        """
        Extract parameters from user input
        
        Args:
            user_input: User's action request
            action_type: Type of action
        
        Returns:
            Extracted parameters
        """
        # Simple parameter extraction (would use NER in production)
        params: Dict[str, Any] = {}
        
        if action_type == "create_node":
            # Extract label and properties
            params = {
                "labels": ["Element"],  # Would parse from input
                "properties": {"description": user_input}
            }
        
        elif action_type == "create_relationship":
            params = {
                "from_uri": "unknown",
                "to_uri": "unknown",
                "relationship_type": "RELATES_TO"
            }
        
        elif action_type == "update_properties":
            params = {
                "target_type": "node",
                "uri": "unknown",
                "properties": {"updated": True}
            }
        
        elif action_type == "store_document":
            params = {
                "uri": "document://new",
                "content": user_input,
                "content_type": "json",
                "metadata": {"description": "Stored via ActionAgent"}
            }
        
        elif action_type == "segment_pointcloud":
            params = {
                "input_file": "pointcloud.npy",
                "model": "pointnet"
            }

        elif action_type == "delete":
            params = {
                "uris": ["unknown"],
                "detach": True,
            }
        
        return params
    

    
    def _get_sample_create_node_result(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get sample create node result"""
        return [{
            "status": "success",
            "node_id": "element_12345",
            "label": parameters.get("label", "Element"),
            "properties": parameters.get("properties", {})
        }]
    
    def _get_sample_create_relationship_result(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get sample create relationship result"""
        return [{
            "status": "success",
            "relationship_id": "rel_67890",
            "from": parameters.get("from_node"),
            "to": parameters.get("to_node"),
            "type": parameters.get("relationship_type")
        }]
    
    def _get_sample_update_result(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get sample update result"""
        return [{
            "status": "success",
            "node_id": parameters.get("node_id"),
            "updated_properties": parameters.get("properties", {}),
            "timestamp": datetime.now().isoformat()
        }]
    
    def _get_sample_store_document_result(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get sample store document result"""
        return [{
            "status": "success",
            "document_uri": parameters.get("uri"),
            "version": 1,
            "stored_at": datetime.now().isoformat()
        }]
    
    def _get_sample_segment_result(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get sample segmentation result"""
        return [{
            "status": "success",
            "input_file": parameters.get("input_file"),
            "segments_found": 12,
            "classes": ["wall", "floor", "ceiling", "door"],
            "processing_time": "2.5s"
        }]
    
    def _generate_response(
        self,
        plan: Dict[str, Any],
        results: List[Dict[str, Any]]
    ) -> str:
        """
        Generate natural language response
        
        Args:
            plan: Action plan
            results: Execution results
        
        Returns:
            Natural language response
        """
        action_type = plan["action_type"]
        
        if not results or results[0].get("status") != "success":
            return f"Action failed: {action_type}"
        
        if action_type == "create_node":
            node_id = results[0].get("node_id", "unknown")
            return f"Successfully created node: {node_id}"
        
        elif action_type == "create_relationship":
            rel_id = results[0].get("relationship_id", "unknown")
            return f"Successfully created relationship: {rel_id}"
        
        elif action_type == "update_properties":
            node_id = results[0].get("node_id", "unknown")
            return f"Successfully updated properties for: {node_id}"
        
        elif action_type == "store_document":
            uri = results[0].get("document_uri", "unknown")
            return f"Successfully stored document: {uri}"
        
        elif action_type == "segment_pointcloud":
            segments = results[0].get("segments_found", 0)
            classes = results[0].get("classes", [])
            return f"Point cloud segmentation complete: {segments} segments found ({', '.join(classes[:3])}...)"
        
        else:
            return f"Action completed: {action_type}"


# ============================================================================
# Integration with Agent Orchestrator
# ============================================================================

async def action_agent_node(state: AgentState) -> AgentState:
    """
    Action agent node for LangGraph
    
    This replaces the placeholder in agent_orchestrator.py
    """
    agent = ActionAgent()
    return await agent.process(state)


# ============================================================================
# Testing
# ============================================================================

async def test_action_agent():
    """Test action agent"""
    print("=" * 60)
    print("Action Agent Test")
    print("=" * 60)
    
    agent = ActionAgent()
    
    # Test actions
    test_actions = [
        "Create a new wall element with fire rating 90",
        "Update the thickness of Wall-01 to 250mm",
        "Store IFC document building.ifc",
        "Segment point cloud Area_1_conferenceRoom_1_point.npy",
        "Create relationship between Wall-01 and Space-101"
    ]
    
    for action in test_actions:
        print(f"\n{'='*60}")
        print(f"Action: {action}")
        print(f"{'='*60}")
        
        # Create test state
        if LANGCHAIN_AVAILABLE:
            state: AgentState = {
                "messages": [make_human_message(content=action)],
                "user_input": action,
                "intent": "action",
                "metadata": {"test": True, "user_id": "test_user", "session_id": "test_session"}
            }
        else:
            state = {
                "messages": [{"type": "human", "content": action}],
                "user_input": action,
                "intent": "action",
                "metadata": {"test": True, "user_id": "test_user", "session_id": "test_session"}
            }
        
        # Process
        result_state = await agent.process(state)
        
        # Show results
        if isinstance(result_state.get("messages", [])[-1] if result_state.get("messages") else {}, dict):
            response = result_state.get("messages", [])[-1].get("content", "No response") if result_state.get("messages") else "No response"
        else:
            response = result_state["messages"][-1].content if result_state.get("messages") else "No response"
        print(f"\nResponse: {response}")
        
        if "mcp_results" in result_state and result_state['mcp_results']:
            result = result_state['mcp_results'][0]
            print(f"Result: {result}")
        
        if "metadata" in result_state and "action_plan" in result_state["metadata"]:
            plan = result_state["metadata"]["action_plan"]
            print(f"Action type: {plan['action_type']}")
            print(f"Tool: {plan['tool']}")
            if plan['requires_confirmation']:
                print("⚠️  Requires user confirmation")
        
        if "error" in result_state:
            print(f"Error: {result_state['error']}")
    
    print(f"\n{'='*60}")
    print("✅ Action Agent test complete")
    
    # Show audit log
    if agent.audit_logger:
        print(f"\n{'='*60}")
        print("Audit Log Summary")
        print(f"{'='*60}")
        recent_events = agent.audit_logger.get_recent_events(limit=5)
        for event in recent_events:
            print(f"{event.timestamp} | {event.event_type:20} | {event.action:20} | {event.result}")
        print(f"{'='*60}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_action_agent())
