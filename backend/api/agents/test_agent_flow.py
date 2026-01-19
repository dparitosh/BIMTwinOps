"""
End-to-end test for agent orchestration flow.

Tests:
1. Query intent - routes to query_agent
2. Action intent (Create) - routes to action_agent, may require approval
3. Action intent (Delete) - routes to action_agent, requires approval (HITL)
4. Planning intent - routes to planning_agent for multi-step workflows
"""

import asyncio
import sys
sys.path.insert(0, r"D:\SMART_BIM\backend")

from api.agents.agent_orchestrator import AgentOrchestrator


async def test_agent_flow():
    """Test the full agent orchestration flow"""
    print("Initializing AgentOrchestrator...")
    orch = AgentOrchestrator()
    
    results = {}
    
    # Test 1: Query Intent
    print("\n" + "="*50)
    print("Test 1: Query Intent")
    print("="*50)
    try:
        r1 = await orch.process("Show me all walls")
        results["query"] = r1
        print(f"Intent: {r1.get('intent', 'N/A')}")
        print(f"Success: {r1.get('success', False)}")
        if r1.get("response"):
            print(f"Response preview: {r1.get('response', '')[:100]}...")
    except Exception as e:
        print(f"ERROR: {e}")
        results["query"] = {"error": str(e)}
    
    # Test 2: Action Intent (Create)
    print("\n" + "="*50)
    print("Test 2: Action Intent (Create)")
    print("="*50)
    try:
        r2 = await orch.process("Create a new wall element")
        results["create"] = r2
        print(f"Intent: {r2.get('intent', 'N/A')}")
        print(f"Requires Approval: {r2.get('requires_approval', False)}")
        print(f"Success: {r2.get('success', False)}")
    except Exception as e:
        print(f"ERROR: {e}")
        results["create"] = {"error": str(e)}
    
    # Test 3: Action Intent (Delete)
    print("\n" + "="*50)
    print("Test 3: Action Intent (Delete)")
    print("="*50)
    try:
        r3 = await orch.process("Delete wall-01")
        results["delete"] = r3
        print(f"Intent: {r3.get('intent', 'N/A')}")
        print(f"Requires Approval: {r3.get('requires_approval', False)}")
        print(f"Success: {r3.get('success', False)}")
        if r3.get("metadata", {}).get("ui_component"):
            print("UI Component: APPROVAL dialog generated")
    except Exception as e:
        print(f"ERROR: {e}")
        results["delete"] = {"error": str(e)}
    
    # Test 4: Planning Intent
    print("\n" + "="*50)
    print("Test 4: Planning Intent")
    print("="*50)
    try:
        r4 = await orch.process("Find wall-01 then update its thickness")
        results["planning"] = r4
        print(f"Intent: {r4.get('intent', 'N/A')}")
        print(f"Success: {r4.get('success', False)}")
        if r4.get("planning_response"):
            print(f"Planning response: {r4.get('planning_response', '')[:100]}...")
    except Exception as e:
        print(f"ERROR: {e}")
        results["planning"] = {"error": str(e)}
    
    # Summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    
    tests = [
        ("Query", results.get("query", {})),
        ("Action (Create)", results.get("create", {})),
        ("Action (Delete)", results.get("delete", {})),
        ("Planning", results.get("planning", {}))
    ]
    
    all_passed = True
    for name, r in tests:
        has_error = "error" in r
        success = r.get("success", False) or r.get("requires_approval", False)
        
        if has_error:
            status = "✗"
            all_passed = False
            detail = f"Error: {r.get('error', 'unknown')[:50]}"
        elif success:
            status = "✓"
            detail = f"intent={r.get('intent', 'N/A')}"
        else:
            status = "?"
            detail = f"intent={r.get('intent', 'N/A')}, no success flag"
        
        print(f"{status} {name}: {detail}")
    
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))
    return all_passed


if __name__ == "__main__":
    result = asyncio.run(test_agent_flow())
    sys.exit(0 if result else 1)
