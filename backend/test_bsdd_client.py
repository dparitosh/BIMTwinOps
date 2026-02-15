"""
Quick test of refactored bSDD client with REST APIs
"""
from api.bsdd_client import BSDDClient, BSDDEnvironment

def test_bsdd_client():
    print("=== Testing bSDD Client with REST API ===\n")
    
    # Initialize client
    client = BSDDClient(environment=BSDDEnvironment.PRODUCTION)
    print("✓ Client initialized with User-Agent header\n")
    
    # Get dictionaries
    print("Fetching dictionaries...")
    dicts = client.get_dictionaries()
    print(f"✓ Found {len(dicts)} dictionaries\n")
    
    # Find IFC 4.3
    ifc_dicts = [d for d in dicts if 'IFC' in d.name.upper() and '4.3' in d.version]
    if not ifc_dicts:
        print("✗ IFC 4.3 not found")
        return
    
    ifc = ifc_dicts[0]
    print(f"✓ Found IFC 4.3 dictionary:")
    print(f"  Name: {ifc.name}")
    print(f"  Version: {ifc.version}")
    print(f"  Status: {ifc.status}")
    print(f"  URI: {ifc.uri}\n")
    
    # Get classes (with pagination to get all)
    print("Fetching ALL classes from IFC 4.3 (with pagination, may take 1-2 minutes)...")
    try:
        classes = client.get_dictionary_classes(ifc.uri, fetch_all=True)
        print(f"✓ Successfully fetched {len(classes)} classes\n")
        
        # Show sample classes
        print("Sample classes:")
        for c in classes[:10]:
            print(f"  - {c.name} ({c.code})")
        
        # Count by type
        wall_classes = [c for c in classes if 'wall' in c.name.lower()]
        door_classes = [c for c in classes if 'door' in c.name.lower()]
        window_classes = [c for c in classes if 'window' in c.name.lower()]
        
        print(f"\n✓ Class counts:")
        print(f"  Total classes: {len(classes)}")
        print(f"  Wall-related: {len(wall_classes)}")
        print(f"  Door-related: {len(door_classes)}")
        print(f"  Window-related: {len(window_classes)}")
        
    except Exception as e:
        print(f"✗ Error fetching classes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bsdd_client()
