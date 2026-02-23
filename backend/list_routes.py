"""
List all registered routes in the FastAPI app
"""
import requests

try:
    # Get OpenAPI schema
    response = requests.get("http://127.0.0.1:8008/openapi.json")
    schema = response.json()
    
    print("=" * 80)
    print("All registered routes in FastAPI:")
    print("=" * 80)
    
    paths = schema.get("paths", {})
    for path, methods in sorted(paths.items()):
        for method, details in methods.items():
            if method in ["get", "post", "put", "delete", "patch"]:
                summary = details.get("summary", "No summary")
                print(f"{method.upper():6} {path:50} - {summary}")
    
    print("\n" + "=" * 80)
    print(f"Total endpoints: {sum(len([m for m in methods if m in ['get', 'post', 'put', 'delete', 'patch']]) for methods in paths.values())}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
