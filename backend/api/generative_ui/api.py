"""
FastAPI Integration for Generative UI
SSE endpoints for streaming UI components to React frontend.

This module provides REST/SSE endpoints for:
1. Component generation from queries
2. Streaming UI updates
3. Integration with agent orchestrator

Usage:
    from fastapi import FastAPI
    from generative_ui.api import router
    
    app = FastAPI()
    app.include_router(router, prefix="/api/ui")
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, AsyncIterator
import logging

from .ui_generator import (
    ComponentGenerator,
    StreamingUIGenerator,
    AgentResponseConverter,
    StreamEvent,
    StreamEventType,
)

# Import agent orchestrator
from ..agents.agent_orchestrator import AgentOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Generative UI"])

# Initialize services
component_generator = ComponentGenerator()
streaming_generator = StreamingUIGenerator()
response_converter = AgentResponseConverter()
agent_orchestrator = AgentOrchestrator()


# ============================================================================
# Request/Response Models
# ============================================================================

class GenerateUIRequest(BaseModel):
    """Request to generate UI from query"""
    query: str
    thread_id: str = "default"
    streaming: bool = True


class ComponentResponse(BaseModel):
    """Response with generated components"""
    components: list[Dict[str, Any]]
    metadata: Dict[str, Any]


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/generate", response_model=ComponentResponse)
async def generate_ui(request: GenerateUIRequest):
    """
    Generate UI components from natural language query
    
    Example:
        POST /api/ui/generate
        {
            "query": "Show me all walls with fire rating > 60",
            "thread_id": "session_123"
        }
    
    Returns:
        {
            "components": [...],
            "metadata": {...}
        }
    """
    try:
        logger.info("Generating UI for query: %s", request.query)
        
        # Process query through agent orchestrator
        agent_result = await agent_orchestrator.process(
            user_input=request.query,
            thread_id=request.thread_id or "default"
        )
        
        # Convert agent response to UI components
        # For now, create sample components based on intent
        components = []
        
        if agent_result["intent"] == "query":
            # Create sample table for query results
            table = component_generator.create_table(
                columns=[
                    {"key": "element", "label": "Element", "type": "text"},
                    {"key": "type", "label": "Type", "type": "text"},
                    {"key": "rating", "label": "Fire Rating", "type": "number"}
                ],
                data=[
                    {"element": "Wall-01", "type": "IfcWall", "rating": 90},
                    {"element": "Wall-02", "type": "IfcWall", "rating": 120}
                ],
                title="Query Results"
            )
            components.append(table)
        
        elif agent_result["intent"] == "action":
            meta = agent_result.get("state_metadata", {}) or {}
            pending_id = meta.get("pending_action_id")

            if pending_id:
                alert = component_generator.create_alert(
                    message=(
                        "Action requires approval before execution. "
                        f"Pending action id: {pending_id}"
                    ),
                    severity="warning",
                )
                components.append(alert)

                actions_card = component_generator.create_card(
                    title="Approval Required",
                    content=(
                        "Approve to execute, or reject to cancel. "
                        f"Approve: POST /api/approvals/{pending_id}/approve  |  "
                        f"Reject: POST /api/approvals/{pending_id}/reject"
                    ),
                )
                components.append(actions_card)

            else:
                alert = component_generator.create_alert(
                    message=f"Action processed: {request.query}",
                    severity="success"
                )
                components.append(alert)
        
        else:
            # Unknown intent - show message card
            card = component_generator.create_card(
                title="Response",
                content=agent_result["response"]
            )
            components.append(card)
        
        return {
            "components": [component_generator.to_dict(c) for c in components],
            "metadata": {
                "intent": agent_result["intent"],
                "thread_id": request.thread_id,
                "component_count": len(components)
            }
        }
    
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("UI generation failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/stream/{thread_id}")
async def stream_ui_updates(thread_id: str):
    """
    Stream UI component updates via SSE
    
    Subscribe to this endpoint to receive real-time UI updates
    as the agent processes data.
    
    Example:
        const eventSource = new EventSource('/api/ui/stream/session_123');
        eventSource.addEventListener('component', (e) => {
            const component = JSON.parse(e.data);
            renderComponent(component);
        });
    """
    logger.info("Starting UI stream for thread_id=%s", thread_id)

    async def event_generator() -> AsyncIterator[str]:
        """Generate SSE events"""
        try:
            # For now, send a sample stream
            # In production, this would subscribe to agent orchestrator events
            
            sample_components = [
                component_generator.create_alert(
                    message="Processing query...",
                    severity="info"
                ),
                component_generator.create_table(
                    columns=[{"key": "id", "label": "ID", "type": "text"}],
                    data=[{"id": "sample"}],
                    title="Results"
                )
            ]
            
            async for event in streaming_generator.stream_components(sample_components):
                yield event
        
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Streaming error")
            yield streaming_generator.format_sse(
                StreamEvent(event=StreamEventType.ERROR, data={"error": str(e)})
            )
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.post("/convert")
async def convert_response(response_data: Dict[str, Any]):
    """
    Convert structured agent response to UI components
    
    Internal endpoint used by agents to generate UI from their responses.
    
    Example:
        POST /api/ui/convert
        {
            "results": [...],
            "title": "Query Results"
        }
    """
    try:
        components = response_converter.convert(response_data)
        
        return {
            "components": [component_generator.to_dict(c) for c in components],
            "metadata": {
                "component_count": len(components)
            }
        }
    
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("Conversion failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "generative_ui",
        "version": "0.1.0"
    }
