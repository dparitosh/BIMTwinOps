"""
Generative UI System
Dynamic React component generation from agent responses.

This module implements ADR-004 (Generative UI) providing:
1. Component generation from structured data
2. Server-Sent Events (SSE) streaming
3. React component templates
4. UI state management

Architecture:
- Agent Response → UI Generator → Component Stream → React Frontend
- Templates: Tables, Charts, Forms, 3D Viewers, Property Panels
- Protocol: SSE with JSON payloads
- State: Redux-compatible actions

Principles:
1. Declarative: Generate UI from data, not imperative commands
2. Composable: Components nest and combine
3. Streaming: Progressive rendering as data arrives
4. Type-Safe: JSON schemas for validation

References:
- Vercel AI SDK: https://sdk.vercel.ai/docs
- React Server Components: https://react.dev/reference/rsc/server-components
"""

from typing import Dict, Any, List, Optional, Literal, Union, AsyncIterator
from enum import Enum
from pydantic import BaseModel, Field
import json
import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Component Schema Definitions
# ============================================================================

class ComponentType(str, Enum):
    """Supported UI component types"""
    TABLE = "table"
    CHART = "chart"
    FORM = "form"
    PROPERTY_PANEL = "property_panel"
    VIEWER_3D = "viewer_3d"
    CARD = "card"
    LIST = "list"
    ALERT = "alert"
    LOADING = "loading"
    ERROR = "error"


class ChartType(str, Enum):
    """Chart visualization types"""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    HEATMAP = "heatmap"


class UIComponent(BaseModel):
    """
    Base UI component schema
    
    All generated components follow this structure for consistency
    and type safety on the frontend.
    """
    id: str = Field(description="Unique component identifier")
    type: ComponentType = Field(description="Component type")
    props: Dict[str, Any] = Field(default_factory=dict, description="Component properties")
    children: Optional[List['UIComponent']] = Field(default=None, description="Nested components")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Component metadata")


class TableComponent(BaseModel):
    """Table component specification"""
    id: str
    type: Literal[ComponentType.TABLE] = ComponentType.TABLE
    props: Dict[str, Any] = Field(default_factory=lambda: {
        "columns": [],
        "data": [],
        "sortable": True,
        "filterable": True,
        "paginated": True,
        "pageSize": 10
    })


class ChartComponent(BaseModel):
    """Chart component specification"""
    id: str
    type: Literal[ComponentType.CHART] = ComponentType.CHART
    props: Dict[str, Any] = Field(default_factory=lambda: {
        "chartType": "bar",
        "data": [],
        "xAxis": None,
        "yAxis": None,
        "title": "",
        "legend": True
    })


class PropertyPanelComponent(BaseModel):
    """Property panel component specification"""
    id: str
    type: Literal[ComponentType.PROPERTY_PANEL] = ComponentType.PROPERTY_PANEL
    props: Dict[str, Any] = Field(default_factory=lambda: {
        "title": "",
        "properties": [],
        "editable": False,
        "grouped": True
    })


# ============================================================================
# Streaming Protocol
# ============================================================================

class StreamEvent(BaseModel):
    """Server-Sent Event structure"""
    event: str = Field(description="Event type")
    data: Dict[str, Any] = Field(description="Event payload")
    id: Optional[str] = Field(default=None, description="Event ID for replay")
    retry: Optional[int] = Field(default=None, description="Retry interval (ms)")


class StreamEventType(str, Enum):
    """SSE event types"""
    COMPONENT = "component"
    UPDATE = "update"
    COMPLETE = "complete"
    ERROR = "error"
    PROGRESS = "progress"


# ============================================================================
# Component Generator
# ============================================================================

class ComponentGenerator:
    """
    Generate React components from structured data
    
    Converts agent responses (tables, charts, properties) into
    React component specifications that the frontend can render.
    
    Usage:
        generator = ComponentGenerator()
        component = generator.create_table(columns, data)
        json_spec = generator.to_json(component)
    """
    
    def __init__(self):
        self.component_counter = 0
    
    def _generate_id(self, prefix: str = "component") -> str:
        """Generate unique component ID"""
        self.component_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{prefix}_{timestamp}_{self.component_counter}"
    
    def create_table(
        self,
        columns: List[Dict[str, Any]],
        data: List[Dict[str, Any]],
        title: Optional[str] = None,
        sortable: bool = True,
        filterable: bool = True
    ) -> UIComponent:
        """
        Create table component
        
        Args:
            columns: Column definitions [{"key": "name", "label": "Name", "type": "text"}]
            data: Row data [{"name": "Wall-01", "type": "IfcWall"}]
            title: Optional table title
            sortable: Enable column sorting
            filterable: Enable column filtering
        
        Returns:
            UIComponent for table
        """
        component_id = self._generate_id("table")
        
        return UIComponent(
            id=component_id,
            type=ComponentType.TABLE,
            props={
                "title": title,
                "columns": columns,
                "data": data,
                "sortable": sortable,
                "filterable": filterable,
                "paginated": len(data) > 10,
                "pageSize": 10
            },
            metadata={
                "created_at": datetime.now().isoformat(),
                "row_count": len(data),
                "column_count": len(columns)
            }
        )
    
    def create_chart(
        self,
        chart_type: ChartType,
        data: List[Dict[str, Any]],
        x_axis: str,
        y_axis: str,
        title: Optional[str] = None
    ) -> UIComponent:
        """
        Create chart component
        
        Args:
            chart_type: Type of chart (bar, line, pie, etc.)
            data: Chart data points
            x_axis: X-axis field name
            y_axis: Y-axis field name
            title: Chart title
        
        Returns:
            UIComponent for chart
        """
        component_id = self._generate_id("chart")
        
        return UIComponent(
            id=component_id,
            type=ComponentType.CHART,
            props={
                "chartType": chart_type.value,
                "data": data,
                "xAxis": x_axis,
                "yAxis": y_axis,
                "title": title,
                "legend": True,
                "responsive": True
            },
            metadata={
                "created_at": datetime.now().isoformat(),
                "data_points": len(data)
            }
        )
    
    def create_property_panel(
        self,
        properties: List[Dict[str, Any]],
        title: str = "Properties",
        editable: bool = False,
        grouped: bool = True
    ) -> UIComponent:
        """
        Create property panel component
        
        Args:
            properties: Property list [{"name": "Fire Rating", "value": "90 min", "group": "Safety"}]
            title: Panel title
            editable: Allow editing
            grouped: Group properties by category
        
        Returns:
            UIComponent for property panel
        """
        component_id = self._generate_id("properties")
        
        return UIComponent(
            id=component_id,
            type=ComponentType.PROPERTY_PANEL,
            props={
                "title": title,
                "properties": properties,
                "editable": editable,
                "grouped": grouped
            },
            metadata={
                "created_at": datetime.now().isoformat(),
                "property_count": len(properties)
            }
        )
    
    def create_card(
        self,
        title: str,
        content: Union[str, UIComponent, List[UIComponent]],
        actions: Optional[List[Dict[str, Any]]] = None
    ) -> UIComponent:
        """
        Create card component (container)
        
        Args:
            title: Card title
            content: Card content (text or nested components)
            actions: Action buttons [{"label": "Edit", "action": "edit"}]
        
        Returns:
            UIComponent for card
        """
        component_id = self._generate_id("card")

        # Handle nested components
        children: Optional[List[UIComponent]] = None
        content_text: Optional[str] = None
        if isinstance(content, list):
            children = content
        elif isinstance(content, UIComponent):
            children = [content]
        else:
            content_text = content
        
        return UIComponent(
            id=component_id,
            type=ComponentType.CARD,
            props={
                "title": title,
                "content": content_text,
                "actions": actions or []
            },
            children=children,
            metadata={
                "created_at": datetime.now().isoformat()
            }
        )
    
    def create_alert(
        self,
        message: str,
        severity: Literal["info", "warning", "error", "success"] = "info",
        dismissible: bool = True
    ) -> UIComponent:
        """
        Create alert component
        
        Args:
            message: Alert message
            severity: Alert severity level
            dismissible: Can be dismissed
        
        Returns:
            UIComponent for alert
        """
        component_id = self._generate_id("alert")
        
        return UIComponent(
            id=component_id,
            type=ComponentType.ALERT,
            props={
                "message": message,
                "severity": severity,
                "dismissible": dismissible
            },
            metadata={
                "created_at": datetime.now().isoformat()
            }
        )
    
    def to_json(self, component: UIComponent) -> str:
        """Convert component to JSON string"""
        return component.model_dump_json(exclude_none=True, indent=2)
    
    def to_dict(self, component: UIComponent) -> Dict[str, Any]:
        """Convert component to dictionary"""
        return component.model_dump(exclude_none=True)


# ============================================================================
# Streaming UI Generator
# ============================================================================

class StreamingUIGenerator:
    """
    Stream UI components via Server-Sent Events
    
    Enables progressive rendering as agent processes data.
    Frontend subscribes to SSE endpoint and renders components as they arrive.
    
    Usage:
        generator = StreamingUIGenerator()
        async for event in generator.stream_components(components):
            # Send to frontend via SSE
            yield event
    """
    
    def __init__(self):
        self.component_generator = ComponentGenerator()
    
    async def stream_components(
        self,
        components: List[UIComponent],
        delay_ms: int = 100
    ) -> AsyncIterator[str]:
        """
        Stream components with progressive rendering
        
        Args:
            components: List of components to stream
            delay_ms: Delay between component sends (simulates processing)
        
        Yields:
            SSE-formatted strings
        """
        try:
            # Send start event
            yield self._format_sse(
                StreamEvent(
                    event=StreamEventType.PROGRESS,
                    data={"status": "started", "total": len(components)}
                )
            )
            
            # Stream each component
            for idx, component in enumerate(components):
                await asyncio.sleep(delay_ms / 1000)
                
                yield self._format_sse(
                    StreamEvent(
                        event=StreamEventType.COMPONENT,
                        data={
                            "component": self.component_generator.to_dict(component),
                            "index": idx,
                            "total": len(components)
                        },
                        id=component.id
                    )
                )
            
            # Send completion event
            yield self._format_sse(
                StreamEvent(
                    event=StreamEventType.COMPLETE,
                    data={"status": "completed", "total": len(components)}
                )
            )
            
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Streaming error")
            yield self._format_sse(
                StreamEvent(
                    event=StreamEventType.ERROR,
                    data={"error": str(e)}
                )
            )

    def format_sse(self, event: StreamEvent) -> str:
        """Public wrapper for SSE formatting.

        Prefer this over calling the protected `_format_sse` from outside the class.
        """
        return self._format_sse(event)
    
    def _format_sse(self, event: StreamEvent) -> str:
        """
        Format event as Server-Sent Event string
        
        SSE format:
        event: component
        data: {"component": {...}}
        id: component_123
        
        """
        lines = []
        
        if event.event:
            lines.append(f"event: {event.event}")
        
        if event.data:
            data_json = json.dumps(event.data)
            lines.append(f"data: {data_json}")
        
        if event.id:
            lines.append(f"id: {event.id}")
        
        if event.retry:
            lines.append(f"retry: {event.retry}")
        
        # SSE requires double newline at end
        lines.append("")
        lines.append("")
        
        return "\n".join(lines)


# ============================================================================
# Agent Response to UI Converter
# ============================================================================

class AgentResponseConverter:
    """
    Convert agent responses to UI components
    
    Analyzes agent output and generates appropriate UI components:
    - Tabular data → Table
    - Metrics → Charts
    - Entity properties → Property panels
    - Lists → Cards or lists
    
    Usage:
        converter = AgentResponseConverter()
        components = converter.convert(agent_response)
    """
    
    def __init__(self):
        self.generator = ComponentGenerator()
    
    def convert(self, response_data: Dict[str, Any]) -> List[UIComponent]:
        """
        Convert agent response to UI components
        
        Args:
            response_data: Structured agent response
        
        Returns:
            List of UI components to render
        """
        components = []
        
        # Detect response type and generate appropriate components
        if "results" in response_data and isinstance(response_data["results"], list):
            # Tabular results
            if len(response_data["results"]) > 0:
                columns = self._infer_columns(response_data["results"])
                table = self.generator.create_table(
                    columns=columns,
                    data=response_data["results"],
                    title=response_data.get("title", "Results")
                )
                components.append(table)
        
        if "properties" in response_data and isinstance(response_data["properties"], list):
            # Property list
            panel = self.generator.create_property_panel(
                properties=response_data["properties"],
                title=response_data.get("title", "Properties")
            )
            components.append(panel)
        
        if "metrics" in response_data:
            # Metrics visualization
            chart_data = self._prepare_chart_data(response_data["metrics"])
            if chart_data:
                chart = self.generator.create_chart(
                    chart_type=ChartType.BAR,
                    data=chart_data["data"],
                    x_axis=chart_data["x"],
                    y_axis=chart_data["y"],
                    title=response_data.get("title", "Metrics")
                )
                components.append(chart)
        
        if "message" in response_data:
            # Text message as card
            card = self.generator.create_card(
                title="Response",
                content=response_data["message"]
            )
            components.append(card)
        
        return components
    
    def _infer_columns(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Infer column definitions from data"""
        if not data:
            return []
        
        first_row = data[0]
        columns = []
        
        for key, value in first_row.items():
            col_type = "text"
            if isinstance(value, (int, float)):
                col_type = "number"
            elif isinstance(value, bool):
                col_type = "boolean"
            
            columns.append({
                "key": key,
                "label": key.replace("_", " ").title(),
                "type": col_type,
                "sortable": True
            })
        
        return columns
    
    def _prepare_chart_data(self, metrics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert metrics to chart-compatible format"""
        # Simple conversion: assume metrics is {label: value}
        if not metrics:
            return None
        
        data = [
            {"label": k, "value": v}
            for k, v in metrics.items()
            if isinstance(v, (int, float))
        ]
        
        if not data:
            return None
        
        return {
            "data": data,
            "x": "label",
            "y": "value"
        }


# ============================================================================
# Testing & Examples
# ============================================================================

async def test_generative_ui():
    """Test generative UI system"""
    
    print("=" * 60)
    print("Generative UI System Test")
    print("=" * 60)
    
    generator = ComponentGenerator()
    
    # Test 1: Create table
    print("\n1. Table Component")
    print("-" * 60)
    
    table = generator.create_table(
        columns=[
            {"key": "name", "label": "Name", "type": "text"},
            {"key": "type", "label": "Type", "type": "text"},
            {"key": "fire_rating", "label": "Fire Rating", "type": "number"}
        ],
        data=[
            {"name": "Wall-01", "type": "IfcWall", "fire_rating": 90},
            {"name": "Wall-02", "type": "IfcWall", "fire_rating": 60},
            {"name": "Door-01", "type": "IfcDoor", "fire_rating": 30}
        ],
        title="Building Elements"
    )
    
    print(generator.to_json(table))
    
    # Test 2: Create chart
    print("\n2. Chart Component")
    print("-" * 60)
    
    chart = generator.create_chart(
        chart_type=ChartType.BAR,
        data=[
            {"element": "Walls", "count": 45},
            {"element": "Doors", "count": 12},
            {"element": "Windows", "count": 23}
        ],
        x_axis="element",
        y_axis="count",
        title="Element Distribution"
    )
    
    print(generator.to_json(chart))
    
    # Test 3: Create property panel
    print("\n3. Property Panel Component")
    print("-" * 60)
    
    properties = generator.create_property_panel(
        properties=[
            {"name": "Fire Rating", "value": "90 min", "group": "Safety"},
            {"name": "Material", "value": "Concrete", "group": "Physical"},
            {"name": "Thickness", "value": "200 mm", "group": "Physical"}
        ],
        title="Wall Properties"
    )
    
    print(generator.to_json(properties))
    
    # Test 4: Streaming
    print("\n4. Streaming Test")
    print("-" * 60)
    
    streaming = StreamingUIGenerator()
    components = [table, chart, properties]
    
    print("Streaming components...")
    async for event in streaming.stream_components(components, delay_ms=500):
        print(event)
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_generative_ui())
