"""
Planning Agent

Coordinates multi-step workflows by:
1. Analyzing user requests
2. Breaking down into subtasks
3. Routing to Query/Action agents
4. Tracking progress and dependencies
5. Aggregating results

Architecture:
- Uses LLM for task decomposition
- Maintains workflow state
- Handles agent coordination
- Provides progress updates

References:
- ADR-001: Agent Architecture
- ADR-002: Security Layer Integration
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

# LangChain imports
try:
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    HumanMessage = lambda content: {"type": "human", "content": content}
    AIMessage = lambda content: {"type": "ai", "content": content}
    SystemMessage = lambda content: {"type": "system", "content": content}

# Agent imports
try:
    from .query_agent import QueryAgent
    from .action_agent import ActionAgent
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False
    QueryAgent = None
    ActionAgent = None

# Security imports
try:
    from ..security.security_layer import SecurityLayer, AuditLogger, AuditEventType
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks in a workflow"""
    QUERY = "query"  # Read-only information retrieval
    ACTION = "action"  # State modification
    ANALYSIS = "analysis"  # Data processing/analysis
    WAIT = "wait"  # Wait for dependency


class TaskStatus(Enum):
    """Status of individual tasks"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"  # Waiting for dependency


class WorkflowTask:
    """Represents a single task in a workflow"""
    
    def __init__(
        self,
        task_id: str,
        task_type: TaskType,
        description: str,
        agent: str,
        parameters: Dict[str, Any],
        dependencies: List[str] = None
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.description = description
        self.agent = agent
        self.parameters = parameters
        self.dependencies = dependencies or []
        self.status = TaskStatus.PENDING
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "description": self.description,
            "agent": self.agent,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class PlanningAgent:
    """
    Planning Agent for workflow coordination
    
    Responsibilities:
    - Task decomposition
    - Dependency management
    - Agent routing
    - Progress tracking
    """
    
    def __init__(self, llm: Optional[Any] = None):
        """
        Initialize planning agent
        
        Args:
            llm: Language model for task decomposition
        """
        self.llm = llm
        self.query_agent = QueryAgent() if AGENTS_AVAILABLE and QueryAgent else None
        self.action_agent = ActionAgent() if AGENTS_AVAILABLE and ActionAgent else None
        self.security = SecurityLayer() if SECURITY_AVAILABLE else None
        self.audit_logger = AuditLogger() if SECURITY_AVAILABLE else None
        
        logger.info(f"PlanningAgent initialized (LLM: {'available' if llm else 'unavailable'})")
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user request through workflow planning
        
        Args:
            state: Agent state with user input
        
        Returns:
            Updated state with workflow results
        """
        # Extract user input from various state formats
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, 'content'):
                user_input = last_message.content
            elif isinstance(last_message, dict):
                user_input = last_message.get("content", "")
            else:
                user_input = str(last_message)
        else:
            user_input = state.get("user_input", "")
        
        logger.info(f"Planning Agent: Processing workflow request")
        
        # Audit log
        if self.audit_logger:
            self.audit_logger.log_event(
                event_type=AuditEventType.USER_INPUT,
                action="workflow_planning",
                status="started",
                details={"user_input": user_input}
            )
        
        try:
            # 1. Decompose into tasks
            tasks = await self._decompose_tasks(user_input)
            
            # 2. Execute workflow
            results = await self._execute_workflow(tasks)
            
            # 3. Aggregate results
            response = self._aggregate_results(tasks, results)
            
            # Audit log success
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type=AuditEventType.AGENT_ACTION,
                    action="workflow_completed",
                    status="success",
                    details={"task_count": len(tasks)}
                )
            
            # Update state
            state["planning_response"] = response
            state["workflow_tasks"] = [task.to_dict() for task in tasks]
            state["messages"].append(AIMessage(content=response))
            
            return state
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type=AuditEventType.ERROR,
                    action="workflow_failed",
                    status="error",
                    details={"error": str(e)}
                )
            
            state["planning_response"] = f"Workflow failed: {str(e)}"
            state["messages"].append(AIMessage(content=f"Error: {str(e)}"))
            return state
    
    async def _decompose_tasks(self, user_input: str) -> List[WorkflowTask]:
        """
        Decompose user request into executable tasks
        
        Args:
            user_input: User's natural language request
        
        Returns:
            List of workflow tasks
        """
        # Simple rule-based decomposition (can be enhanced with LLM)
        tasks = []
        
        # Pattern matching for common workflows
        if "find" in user_input.lower() and "then" in user_input.lower():
            # Multi-step: Find X, then do Y
            tasks.append(WorkflowTask(
                task_id="task_1",
                task_type=TaskType.QUERY,
                description="Find requested information",
                agent="query",
                parameters={"query": user_input.split("then")[0].strip()}
            ))
            tasks.append(WorkflowTask(
                task_id="task_2",
                task_type=TaskType.ACTION,
                description="Perform action with results",
                agent="action",
                parameters={"action": user_input.split("then")[1].strip()},
                dependencies=["task_1"]
            ))
        
        elif "analyze" in user_input.lower() or "compare" in user_input.lower():
            # Analysis workflow
            tasks.append(WorkflowTask(
                task_id="task_1",
                task_type=TaskType.QUERY,
                description="Retrieve data for analysis",
                agent="query",
                parameters={"query": user_input}
            ))
            tasks.append(WorkflowTask(
                task_id="task_2",
                task_type=TaskType.ANALYSIS,
                description="Analyze retrieved data",
                agent="planning",
                parameters={"analysis_type": "comparison"},
                dependencies=["task_1"]
            ))
        
        elif any(keyword in user_input.lower() for keyword in ["create", "update", "delete", "store"]):
            # Action workflow
            tasks.append(WorkflowTask(
                task_id="task_1",
                task_type=TaskType.ACTION,
                description="Execute requested action",
                agent="action",
                parameters={"action": user_input}
            ))
        
        else:
            # Default: Single query task
            tasks.append(WorkflowTask(
                task_id="task_1",
                task_type=TaskType.QUERY,
                description="Retrieve requested information",
                agent="query",
                parameters={"query": user_input}
            ))
        
        logger.info(f"Decomposed into {len(tasks)} tasks")
        return tasks
    
    async def _execute_workflow(self, tasks: List[WorkflowTask]) -> Dict[str, Any]:
        """
        Execute workflow tasks with dependency management
        
        Args:
            tasks: List of workflow tasks
        
        Returns:
            Dictionary of task results
        """
        results = {}
        completed = set()
        
        # Execute tasks respecting dependencies
        max_iterations = len(tasks) * 2  # Prevent infinite loops
        iteration = 0
        
        while len(completed) < len(tasks) and iteration < max_iterations:
            iteration += 1
            
            for task in tasks:
                # Skip if already completed
                if task.task_id in completed:
                    continue
                
                # Check if dependencies are met
                if not all(dep in completed for dep in task.dependencies):
                    task.status = TaskStatus.BLOCKED
                    continue
                
                # Execute task
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                
                try:
                    if task.agent == "query" and self.query_agent:
                        state = {"user_input": task.parameters.get("query", "")}
                        result_state = await self.query_agent.process(state)
                        task.result = result_state.get("query_response", "No results")
                    
                    elif task.agent == "action" and self.action_agent:
                        state = {"user_input": task.parameters.get("action", "")}
                        result_state = await self.action_agent.process(state)
                        task.result = result_state.get("action_response", "Action completed")
                    
                    elif task.agent == "planning":
                        # Self-handled analysis task
                        task.result = "Analysis completed"
                    
                    else:
                        task.result = "Agent unavailable"
                    
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.now()
                    completed.add(task.task_id)
                    results[task.task_id] = task.result
                    
                    logger.info(f"Task {task.task_id} completed")
                    
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    task.completed_at = datetime.now()
                    logger.error(f"Task {task.task_id} failed: {str(e)}")
                    
                    # Stop workflow on failure (can be made configurable)
                    break
            
            # Small delay between iterations
            await asyncio.sleep(0.1)
        
        return results
    
    def _aggregate_results(self, tasks: List[WorkflowTask], results: Dict[str, Any]) -> str:
        """
        Aggregate task results into final response
        
        Args:
            tasks: List of workflow tasks
            results: Task results dictionary
        
        Returns:
            Aggregated response string
        """
        # Build summary
        summary_parts = []
        
        completed_count = sum(1 for task in tasks if task.status == TaskStatus.COMPLETED)
        failed_count = sum(1 for task in tasks if task.status == TaskStatus.FAILED)
        
        summary_parts.append(f"Workflow execution: {completed_count}/{len(tasks)} tasks completed")
        
        if failed_count > 0:
            summary_parts.append(f"⚠️ {failed_count} task(s) failed")
        
        # Add individual task results
        for task in tasks:
            if task.status == TaskStatus.COMPLETED:
                summary_parts.append(f"\n✓ {task.description}: {task.result}")
            elif task.status == TaskStatus.FAILED:
                summary_parts.append(f"\n✗ {task.description}: {task.error}")
        
        return "\n".join(summary_parts)


# Node function for LangGraph integration
async def planning_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planning agent node for LangGraph workflow
    
    Args:
        state: Current agent state
    
    Returns:
        Updated state
    """
    agent = PlanningAgent()
    return await agent.process(state)


# Test code
if __name__ == "__main__":
    async def test_planning_agent():
        print("=" * 60)
        print("Planning Agent Test")
        print("=" * 60)
        
        agent = PlanningAgent()
        
        # Test 1: Simple query
        print("\nTest 1: Simple query workflow")
        state = {
            "messages": [HumanMessage(content="Show me all walls with fire rating > 60")]
        }
        result = await agent.process(state)
        print(f"Response: {result.get('planning_response', 'No response')}")
        
        # Test 2: Multi-step workflow
        print("\nTest 2: Multi-step workflow")
        state = {
            "messages": [HumanMessage(content="Find wall-01 then update its thickness to 300mm")]
        }
        result = await agent.process(state)
        print(f"Response: {result.get('planning_response', 'No response')}")
        print(f"Tasks: {len(result.get('workflow_tasks', []))} tasks")
        for task_dict in result.get('workflow_tasks', []):
            print(f"  - {task_dict['description']}: {task_dict['status']}")
        
        # Test 3: Analysis workflow
        print("\nTest 3: Analysis workflow")
        state = {
            "messages": [HumanMessage(content="Analyze space utilization in conference rooms")]
        }
        result = await agent.process(state)
        print(f"Response: {result.get('planning_response', 'No response')}")
        
        print("\n" + "=" * 60)
        print("✅ Planning Agent test complete")
        print("=" * 60)
    
    asyncio.run(test_planning_agent())
