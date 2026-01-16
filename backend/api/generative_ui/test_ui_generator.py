"""
Test Generative UI System
"""

import os
import unittest

# Integration script: skip during unit test discovery unless explicitly enabled.
if __name__ != "__main__" and os.getenv("RUN_INTEGRATION_TESTS") != "1":
    raise unittest.SkipTest("Integration script (set RUN_INTEGRATION_TESTS=1 to enable)")

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generative_ui.ui_generator import (
    ComponentGenerator,
    StreamingUIGenerator,
    AgentResponseConverter,
    ComponentType,
    ChartType
)
import asyncio
import json


async def test_component_generation():
    """Test component generation"""
    print("=" * 60)
    print("Component Generation Test")
    print("=" * 60)
    
    generator = ComponentGenerator()
    
    # Test 1: Table
    print("\n1. Table Component")
    table = generator.create_table(
        columns=[
            {"key": "element", "label": "Element", "type": "text"},
            {"key": "type", "label": "Type", "type": "text"},
            {"key": "fire_rating", "label": "Fire Rating (min)", "type": "number"}
        ],
        data=[
            {"element": "Wall-01", "type": "IfcWall", "fire_rating": 90},
            {"element": "Wall-02", "type": "IfcWall", "fire_rating": 120},
            {"element": "Wall-03", "type": "IfcWall", "fire_rating": 60}
        ],
        title="Fire-Rated Walls"
    )
    print(f"✅ Created table component: {table.id}")
    print(f"   Rows: {len(table.props['data'])}")
    print(f"   Columns: {len(table.props['columns'])}")
    
    # Test 2: Chart
    print("\n2. Chart Component")
    chart = generator.create_chart(
        chart_type=ChartType.BAR,
        data=[
            {"category": "Walls", "count": 45},
            {"category": "Doors", "count": 12},
            {"category": "Windows", "count": 23},
            {"category": "Stairs", "count": 5}
        ],
        x_axis="category",
        y_axis="count",
        title="Element Distribution"
    )
    print(f"✅ Created chart component: {chart.id}")
    print(f"   Type: {chart.props['chartType']}")
    print(f"   Data points: {len(chart.props['data'])}")
    
    # Test 3: Property Panel
    print("\n3. Property Panel")
    properties = generator.create_property_panel(
        properties=[
            {"name": "Name", "value": "Wall-01", "group": "Identity"},
            {"name": "Type", "value": "IfcWall", "group": "Identity"},
            {"name": "Fire Rating", "value": "90 minutes", "group": "Safety"},
            {"name": "Material", "value": "Concrete", "group": "Physical"},
            {"name": "Thickness", "value": "200 mm", "group": "Physical"}
        ],
        title="Wall Properties"
    )
    print(f"✅ Created property panel: {properties.id}")
    print(f"   Properties: {len(properties.props['properties'])}")
    
    # Test 4: Card with nested components
    print("\n4. Card with Nested Components")
    card = generator.create_card(
        title="Query Results",
        content=[table, chart],
        actions=[
            {"label": "Export", "action": "export"},
            {"label": "Refresh", "action": "refresh"}
        ]
    )
    print(f"✅ Created card component: {card.id}")
    print(f"   Children: {len(card.children) if card.children else 0}")
    print(f"   Actions: {len(card.props['actions'])}")
    
    return [table, chart, properties, card]


async def test_streaming():
    """Test streaming UI components"""
    print("\n" + "=" * 60)
    print("Streaming Test")
    print("=" * 60)
    
    generator = ComponentGenerator()
    streaming = StreamingUIGenerator()
    
    components = [
        generator.create_alert("Processing query...", severity="info"),
        generator.create_table(
            columns=[{"key": "id", "label": "ID", "type": "text"}],
            data=[{"id": "1"}, {"id": "2"}],
            title="Results"
        ),
        generator.create_alert("Query complete!", severity="success")
    ]
    
    print(f"\nStreaming {len(components)} components...")
    print("-" * 60)
    
    event_count = 0
    async for event in streaming.stream_components(components, delay_ms=300):
        event_count += 1
        lines = event.strip().split('\n')
        for line in lines:
            if line.startswith('event:'):
                print(f"\n{line}")
            elif line.startswith('data:'):
                try:
                    data = json.loads(line[6:])
                    if 'component' in data:
                        comp = data['component']
                        print(f"  Component: {comp['type']} ({comp['id']})")
                    elif 'status' in data:
                        print(f"  Status: {data['status']}")
                except:
                    pass
    
    print(f"\n✅ Streamed {event_count} events")


async def test_response_conversion():
    """Test agent response to UI conversion"""
    print("\n" + "=" * 60)
    print("Response Conversion Test")
    print("=" * 60)
    
    converter = AgentResponseConverter()
    
    # Test case 1: Tabular results
    print("\n1. Converting tabular results")
    response_data = {
        "title": "Query Results",
        "results": [
            {"name": "Wall-01", "type": "IfcWall", "rating": 90},
            {"name": "Wall-02", "type": "IfcWall", "rating": 60}
        ]
    }
    
    components = converter.convert(response_data)
    print(f"✅ Generated {len(components)} component(s)")
    for comp in components:
        print(f"   - {comp.type}: {comp.id}")
    
    # Test case 2: Metrics
    print("\n2. Converting metrics")
    response_data = {
        "title": "Element Count",
        "metrics": {
            "walls": 45,
            "doors": 12,
            "windows": 23
        }
    }
    
    components = converter.convert(response_data)
    print(f"✅ Generated {len(components)} component(s)")
    for comp in components:
        print(f"   - {comp.type}: {comp.id}")
    
    # Test case 3: Properties
    print("\n3. Converting properties")
    response_data = {
        "title": "Element Details",
        "properties": [
            {"name": "Fire Rating", "value": "90 min", "group": "Safety"},
            {"name": "Material", "value": "Concrete", "group": "Physical"}
        ]
    }
    
    components = converter.convert(response_data)
    print(f"✅ Generated {len(components)} component(s)")
    for comp in components:
        print(f"   - {comp.type}: {comp.id}")


async def main():
    """Run all tests"""
    try:
        await test_component_generation()
        await test_streaming()
        await test_response_conversion()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
    
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
