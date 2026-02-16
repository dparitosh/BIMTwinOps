"""
Test if pointcloud routes work by calling the endpoint handler directly
"""
import sys
import asyncio

sys.path.insert(0, 'd:\\SMART_BIM\\backend')

async def test_health():
    """Test the health endpoint directly"""
    try:
        from api.pointcloud_semantic import health_check
        
        result = await health_check()
        print("Direct call successful!")
        print(f"Result: {result}")
        return result
        
    except Exception as e:
        print(f"Error calling health endpoint: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    result = asyncio.run(test_health())
    print(f"\nFinal result: {result}")
