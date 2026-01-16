"""
Generative UI Package
Dynamic React component generation from agent responses.

Modules:
- ui_generator: Component generation and streaming
"""

__version__ = "0.1.0"

from .ui_generator import (
    ComponentGenerator,
    StreamingUIGenerator,
    AgentResponseConverter,
    ComponentType,
    ChartType,
    UIComponent,
    StreamEvent,
    StreamEventType
)

__all__ = [
    "ComponentGenerator",
    "StreamingUIGenerator",
    "AgentResponseConverter",
    "ComponentType",
    "ChartType",
    "UIComponent",
    "StreamEvent",
    "StreamEventType"
]
