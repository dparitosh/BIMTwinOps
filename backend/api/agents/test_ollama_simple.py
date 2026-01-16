"""
Simple Ollama Test (No LangGraph Dependencies)
Tests Ollama connectivity and basic LLM functionality.
"""

import os
import unittest

# Integration script: skip during unit test discovery unless explicitly enabled.
if __name__ != "__main__" and os.getenv("RUN_INTEGRATION_TESTS") != "1":
    raise unittest.SkipTest("Integration script (set RUN_INTEGRATION_TESTS=1 to enable)")


def test_ollama_connection():
    """Test if Ollama is running"""
    import requests  # type: ignore[import-untyped]

    print("=" * 60)
    print("Ollama Connection Test")
    print("=" * 60)
    
    ollama_url = "http://localhost:11434"
    
    try:
        # Check if Ollama is running
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        
        if response.status_code == 200:
            available_models = response.json().get("models", [])
            print(f"\n✅ Ollama is running at {ollama_url}")
            print(f"\nAvailable models: {len(available_models)}")
            
            if available_models:
                for model in available_models:
                    name = model.get("name", "unknown")
                    size = model.get("size", 0) / (1024**3)  # GB
                    modified = model.get("modified_at", "")
                    print(f"  • {name} ({size:.2f} GB) - {modified[:10]}")
                return True, available_models
            else:
                print("\n⚠️  No models installed")
                print("\nTo install a model:")
                print("  ollama pull llama3.2")
                print("  ollama pull mistral")
                return True, []
        else:
            print(f"\n❌ Ollama returned status {response.status_code}")
            return False, []
    
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to Ollama at {ollama_url}")
        print("\n📋 Installation Steps:")
        print("1. Download Ollama from https://ollama.ai")
        print("2. Install and run Ollama")
        print("3. Pull a model: ollama pull llama3.2")
        print("4. Verify: curl http://localhost:11434/api/tags")
        return False, []
    
    except Exception as e:  # noqa: BLE001
        print(f"\n❌ Error: {str(e)}")
        return False, []


def test_ollama_generation():
    """Test Ollama text generation"""
    import requests  # type: ignore[import-untyped]

    print("\n" + "=" * 60)
    print("Ollama Generation Test")
    print("=" * 60)
    
    ollama_url = "http://localhost:11434"
    model = "llama3.2:1b"  # Use the installed model with tag
    
    try:
        print(f"\nSending prompt to {model}...")
        
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": "What is Building Information Modeling (BIM)? Answer in one sentence.",
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("response", "")
            
            print("\n✅ Generation successful!")
            print("\nPrompt: What is Building Information Modeling (BIM)?")
            print(f"Response: {generated_text[:300]}...")
            
            return True
        else:
            print(f"\n❌ Generation failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    
    except Exception as e:  # noqa: BLE001
        print(f"\n❌ Error: {str(e)}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("OLLAMA INTEGRATION TEST SUITE")
    print("Testing: http://localhost:11434")
    print("=" * 60)
    
    # Test 1: Connection
    is_running, models = test_ollama_connection()
    
    if is_running and models:
        # Test 2: Direct API
        test_ollama_generation()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if is_running and models:
        print("✅ Ollama is ready to use!")
        print("\nTo enable in SMART_BIM agents:")
        print("  Set environment variables:")
        print("    LLM_PROVIDER=ollama")
        print("    OLLAMA_BASE_URL=http://localhost:11434")
        print("    OLLAMA_MODEL=llama3.2")
    elif is_running:
        print("⚠️  Ollama is running but no models installed")
        print("  Run: ollama pull llama3.2")
    else:
        print("❌ Ollama is not running")
        print("  Install from: https://ollama.ai")
    
    print("=" * 60)
