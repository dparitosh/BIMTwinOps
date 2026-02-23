# Querying IFC Data in Neo4j - Quick Guide

## 🎯 After Importing Your IFC File

Once you click **"[SAVE] Import to Neo4j"**, you'll have **102 IFC element nodes** in the knowledge graph. Here's how to query them.

---

## 📊 Method 1: GraphQL Playground (Easiest)

**URL**: http://localhost:8008/api/graphql

### Query 1: List All IFC Elements

```graphql
query GetAllIFCElements {
  ifcElements(limit: 20) {
    guid
    ifcType
    name
    properties
  }
}
```

**Response Example**:
```json
{
  "data": {
    "ifcElements": [
      {
        "guid": "2O2Fr$t4X7Zf8NOew3FLOH",
        "ifcType": "IfcWall",
        "name": "Basic Wall:Exterior - Brick:123456",
        "properties": {
          "GlobalId": "2O2Fr$t4X7Zf8NOew3FLOH",
          "OwnerHistory": "...",
          "Name": "Basic Wall",
          "Description": "Exterior Wall"
        }
      }
    ]
  }
}
```

### Query 2: Count Elements by Type

```graphql
query CountByType {
  ifcElementsByType(ifcType: "IfcWall") {
    guid
    name
    ifcType
  }
}
```

### Query 3: Search by Name

```graphql
query SearchElements {
  ifcElements(limit: 100) {
    guid
    ifcType
    name
  }
}
```

Then filter in your app or use text matching.

---

## 🔍 Method 2: Neo4j Browser (Direct Database)

**URL**: http://localhost:7474

**Login**:
- Username: `neo4j`
- Password: (from your `.env` file)

### Cypher Query 1: See All IFC Elements

```cypher
MATCH (e:IfcElement)
RETURN e.guid, e.ifcType, e.name
LIMIT 25
```

### Cypher Query 2: Count Elements by Type

```cypher
MATCH (e:IfcElement)
RETURN e.ifcType AS ElementType, count(*) AS Count
ORDER BY Count DESC
```

**Expected Output**:
```
ElementType     | Count
----------------|------
IfcWall         | 35
IfcSlab         | 12
IfcDoor         | 18
IfcWindow       | 15
IfcColumn       | 8
...
```

### Cypher Query 3: Find Specific Element Types

```cypher
// Find all walls
MATCH (e:IfcElement)
WHERE e.ifcType = 'IfcWall'
RETURN e.guid, e.name, e.properties
LIMIT 10

// Find all doors
MATCH (e:IfcElement)
WHERE e.ifcType = 'IfcDoor'
RETURN e.guid, e.name, e.properties
```

### Cypher Query 4: Spatial Hierarchy

```cypher
// Find building structure
MATCH (building:IfcElement {ifcType: 'IfcBuilding'})
OPTIONAL MATCH (building)-[:CONTAINS]->(storey:IfcElement)
OPTIONAL MATCH (storey)-[:CONTAINS]->(element:IfcElement)
RETURN building.name AS Building, 
       storey.name AS Storey, 
       element.ifcType AS ElementType, 
       count(element) AS Count
```

### Cypher Query 5: Visualize Relationships

```cypher
// Show building structure as graph
MATCH path = (building:IfcElement {ifcType: 'IfcBuilding'})-[:CONTAINS*1..2]->(element)
RETURN path
LIMIT 50
```

---

## 🖥️ Method 3: Knowledge Graph Tab in UI

**In the Frontend** (http://localhost:5173):

1. Click **"Knowledge Graph"** tab (left sidebar)
2. See the spatial graph visualization
3. Click nodes to see properties
4. Use the search bar to find elements

---

## 🔌 Method 4: REST API Queries

### Get All IFC Elements

```bash
curl http://localhost:8008/api/kg/ifc-elements | jq
```

**PowerShell**:
```powershell
Invoke-RestMethod -Uri "http://localhost:8008/api/kg/ifc-elements" | ConvertTo-Json -Depth 5
```

### Count Elements

```bash
curl http://localhost:8008/api/kg/stats
```

---

## 📋 Example Queries for Your AC20-FZK-Haus.ifc

### Find All Walls

```cypher
MATCH (wall:IfcElement {ifcType: 'IfcWall'})
RETURN wall.guid, wall.name, wall.properties
ORDER BY wall.name
```

### Find All Doors and Windows

```cypher
MATCH (openings:IfcElement)
WHERE openings.ifcType IN ['IfcDoor', 'IfcWindow']
RETURN openings.ifcType AS Type, 
       openings.name AS Name, 
       openings.guid AS GUID
ORDER BY Type, Name
```

### Get Building Summary

```cypher
MATCH (e:IfcElement)
RETURN e.ifcType AS ElementType, 
       count(*) AS Count,
       collect(e.name)[0..3] AS Examples
ORDER BY Count DESC
```

### Search by Keyword

```cypher
MATCH (e:IfcElement)
WHERE e.name CONTAINS 'Wall' OR e.name CONTAINS 'Door'
RETURN e.ifcType, e.name, e.guid
LIMIT 20
```

---

## 🤖 Method 5: AI-Powered Queries (Advanced)

Once imported, you can use natural language queries in the **Knowledge Graph** tab:

### Example Natural Language Queries:

1. **"How many walls are in the building?"**
   - Agent translates to Cypher
   - Returns count

2. **"Show me all doors"**
   - Lists all IfcDoor elements

3. **"What types of elements exist?"**
   - Groups by ifcType

4. **"Find elements on the ground floor"**
   - Searches spatial hierarchy

---

## 🔧 Troubleshooting

### No Data Returned?

**Check if import succeeded**:
```cypher
MATCH (e:IfcElement)
RETURN count(e) AS TotalElements
```

If 0, go back to the Revit Integration tab and click **"[SAVE] Import to Neo4j"** again.

### Connection Error?

**Verify Neo4j is running**:
```powershell
Get-NetTCPConnection -LocalPort 7687 -State Listen
```

Should show Neo4j listening on port 7687.

### Verify Backend Configuration

Check [backend/.env](../backend/.env):
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
```

---

## 📚 Next Steps

### After Querying Basic IFC Data:

1. **Add bSDD Classifications**:
   - Get IFC file exported with bSDD Revit Plugin
   - Re-upload and import
   - Query semantic classifications

2. **Add Point Cloud Data**:
   - Upload .npy point cloud file
   - Segment with PointNet
   - Compare BIM vs Point Cloud

3. **Use AI Agents**:
   - GraphQL queries with natural language
   - Automated spatial analysis
   - Property recommendations

---

## 🎯 Quick Test Workflow

### Step-by-Step Test:

```powershell
# 1. Open GraphQL Playground
Start-Process "http://localhost:8008/api/graphql"

# 2. Run this query:
query TestImport {
  ifcElements(limit: 5) {
    guid
    ifcType
    name
  }
}

# 3. Expected: 5 IFC elements returned

# 4. Open Neo4j Browser
Start-Process "http://localhost:7474"

# 5. Run this Cypher:
MATCH (e:IfcElement)
RETURN e.ifcType, count(*) AS Count
ORDER BY Count DESC

# 6. Expected: Table showing element counts
```

---

## 📖 Related Documentation

- [GraphQL API Guide](GRAPHQL_API_GUIDE.md) - Full GraphQL schema
- [Component Architecture](COMPONENT_ARCHITECTURE.md) - System overview
- [Backend Startup Guide](BACKEND_STARTUP_GUIDE.md) - Service management

---

## ✅ Summary

**After clicking "[SAVE] Import to Neo4j":**

✅ **102 nodes** in Neo4j (IfcElement)  
✅ **Basic properties**: GUID, IFC type, name  
✅ **Spatial hierarchy**: Building → Storey → Elements  
✅ **Query methods**: GraphQL, Cypher, REST, UI  

**Missing (needs bSDD file)**:  
❌ Semantic classifications (Uniclass, Omniclass)  
❌ Standardized properties (fire rating, U-value)  
❌ Multi-dictionary mappings  

**Your Next Action:**
1. Click **"[SAVE] Import to Neo4j"** in UI
2. Open GraphQL Playground: http://localhost:8008/api/graphql
3. Run the example queries above
4. Explore your building data! 🏗️
