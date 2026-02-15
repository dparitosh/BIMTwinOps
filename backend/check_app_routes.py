"""
Check if FastAPI app has pointcloud routes registered
"""
import sys
sys.path.insert(0, 'd:\\SMART_BIM\\backend')

from api.main import app

print("=" * 80)
print("All routes in FastAPI app:")
print("=" * 80)

for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        methods_str = str(list(route.methods))
        print(f"{methods_str:20} {route.path}")
    elif hasattr(route, 'path'):
        print(f"{'':20} {route.path}")

print("\n" + "=" * 80)
print("Searching for '/api/pointcloud' routes:")
print("=" * 80)

pointcloud_routes = [r for r in app.routes if hasattr(r, 'path') and '/api/pointcloud' in r.path]
if pointcloud_routes:
    for route in pointcloud_routes:
        methods_str = str(list(route.methods)) if hasattr(route, 'methods') else 'N/A'
        print(f"  {methods_str:20} {route.path}")
else:
    print(" No pointcloud routes found!")

print("\n" + "=" * 80)
print(f"Total routes: {len(app.routes)}")
