"""Check if bSDD classes have properties"""
from api.bsdd_client import BSDDClient

client = BSDDClient()
dicts = client.get_dictionaries()
ifc = next((d for d in dicts if d.name == 'IFC' and '4.3' in d.version), None)

print(f"Testing IFC 4.3: {ifc.uri}\n")

# Get first 5 classes
classes = client.get_dictionary_classes(ifc.uri, fetch_all=False)
print(f"Fetched {len(classes)} classes\n")

# Check first few classes for properties
for i, cls in enumerate(classes[:10]):
    prop_count = len(cls.properties) if cls.properties else 0
    print(f"{i+1}. {cls.name} ({cls.code})")
    print(f"   Properties: {prop_count}")
    if prop_count > 0:
        print(f"   Sample props: {[p.get('name') if isinstance(p, dict) else p.name for p in cls.properties[:3]]}")
    print()
