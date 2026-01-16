"""
Test Ollama Integration
Verifies that Ollama LLM service is accessible and working.
"""

import os
import sys
import unittest

# Integration script: skip during unit test discovery unless explicitly enabled.
if __name__ != "__main__" and os.getenv("RUN_INTEGRATION_TESTS") != "1":
    raise unittest.SkipTest("Integration script (set RUN_INTEGRATION_TESTS=1 to enable)")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio


def test_ollama_connection():
    """Test Ollama API connection"""
    import requests  # type: ignore[import-untyped]

    print("=" * 60)
    print("Testing Ollama Connection")
    print("=" * 60)
    
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    try:
        # Test 1: Check if Ollama is running
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"\n✅ Ollama is running at {ollama_url}")
            print(f"\nAvailable models ({len(models)}):")
            for model in models:
                name = model.get("name", "unknown")
                size = model.get("size", 0) / (1024**3)  # Convert to GB
                print(f"  - {name} ({size:.2f} GB)")
            return True
        else:
            print(f"\n❌ Ollama returned status code: {response.status_code}")
            return False
    
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to Ollama at {ollama_url}")
        print("\nTo start Ollama:")
        print("1. Download from https://ollama.ai")
        print("2. Run: ollama serve")
        print("3. Pull a model: ollama pull llama3.2")
        return False
    
    except (requests.exceptions.RequestException, OSError, ValueError) as e:
        print(f"\n❌ Error: {str(e)}")
        return False


async def test_ollama_llm():
    """Test Ollama LLM via the in-app client"""
    try:
        from .llm import create_llm  # type: ignore
    except ImportError:  # pragma: no cover
        from agents.llm import create_llm  # type: ignore

    print("\n" + "=" * 60)
    print("Testing Ollama LLM Integration")
    print("=" * 60)
    
    # Set environment for Ollama
    os.environ["LLM_PROVIDER"] = "ollama"
    os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
    # Default to an actually-installed tag if OLLAMA_MODEL isn't set
    os.environ["OLLAMA_MODEL"] = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
    
    try:
        llm = create_llm(temperature=0.3)
        print(f"\n✅ LLM initialized: {type(llm).__name__}")
        print(f"Model: {os.getenv('OLLAMA_MODEL')}")
        
        # Test simple query
        print("\nTesting simple query...")
        response = await llm.ainvoke("What is BIM in one sentence?")
        print(f"\nResponse: {response.content[:200]}...")
        
        print("\n✅ Ollama LLM is working!")
        return True
    
    except (RuntimeError, OSError, ValueError) as e:
        print(f"\n❌ Error: {str(e)}")
        return False


async def test_agent_with_ollama():
    """Test Query Agent with Ollama"""
    print("\n" + "=" * 60)
    print("Testing Agent with Ollama")
    print("=" * 60)
    
    # Set environment for Ollama
    os.environ["LLM_PROVIDER"] = "ollama"
    
    try:
        try:
            from .query_agent import QueryAgent  # type: ignore
        except ImportError:  # pragma: no cover
            from agents.query_agent import QueryAgent  # type: ignore
        
        agent = QueryAgent()
        
        state = {
            "user_input": "Show me all walls",
            "messages": [],
            "intent": "query",
            "metadata": {"test": True}
        }
        
        print("\nProcessing query: 'Show me all walls'")
        result = await agent.process(state)
        
        # Extract response
        if result.get('messages'):
            last_msg = result['messages'][-1]
            if isinstance(last_msg, dict):
                response = last_msg.get('content', 'No response')
            else:
                response = last_msg.content
        else:
            response = 'No response'
        
        print(f"\nAgent Response: {response}")
        print(f"Results: {len(result.get('mcp_results', []))} items")
        print("\n✅ Agent works with Ollama!")
        return True
    
    except (ImportError, RuntimeError, OSError, ValueError) as e:
        print(f"\n❌ Error: {str(e)}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Ollama Integration Test Suite")
    print("=" * 60)
    
    # Test 1: Connection
    connection_ok = test_ollama_connection()
    
    if connection_ok:
        # Test 2: LLM
        asyncio.run(test_ollama_llm())
        
        # Test 3: Agent
        asyncio.run(test_agent_with_ollama())
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)
