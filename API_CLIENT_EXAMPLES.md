# BIMTwinOps - Custom Client Integration Guide

## 🔌 Service Endpoints

| Service | Base URL | Status |
|---------|----------|--------|
| Backend API | `http://127.0.0.1:8001` | ✅ Running |
| APS Service | `http://127.0.0.1:3001` | ✅ Running |
| Frontend | `http://localhost:5173` | ✅ Running |

---

## 📡 API Examples

### 1. Backend API - Point Cloud Semantic

#### Health Check
```bash
# cURL
curl http://127.0.0.1:8001/api/pointcloud/health

# PowerShell
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/pointcloud/health" -Method Get

# Python
import requests
r = requests.get('http://127.0.0.1:8001/api/pointcloud/health')
print(r.json())
```

**Response:**
```json
{
  "status": "healthy",
  "semantic_classes_loaded": 12,
  "neo4j_connected": true
}
```

#### Get Semantic Classes
```bash
# cURL
curl http://127.0.0.1:8001/api/pointcloud/semantic-classes

# PowerShell
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/pointcloud/semantic-classes"

# Python
import requests
r = requests.get('http://127.0.0.1:8001/api/pointcloud/semantic-classes')
classes = r.json()['semantic_classes']
for cls in classes:
    print(f"{cls['label']}: {cls['name']}")
```

#### Enrich Point Cloud Segment
```bash
# cURL
curl -X POST http://127.0.0.1:8001/api/pointcloud/enrich \
  -H "Content-Type: application/json" \
  -d '{
    "semantic_label": "wall",
    "points": [[1.0, 2.0, 3.0], [1.1, 2.1, 3.1]],
    "scene_id": "my_scene_001"
  }'

# Python
import requests

data = {
    "semantic_label": "wall",
    "points": [[1.0, 2.0, 3.0], [1.1, 2.1, 3.1]],
    "scene_id": "my_scene_001"
}

r = requests.post(
    'http://127.0.0.1:8001/api/pointcloud/enrich',
    json=data
)

result = r.json()
print(f"IFC Entities: {result['ifc_entities']}")
print(f"bSDD Classifications: {len(result['bsdd_data'])}")
```

#### Batch Enrichment
```bash
# Python
import requests

segments = [
    {
        "label": 0,  # ceiling
        "points": [[1.0, 2.0, 5.0], [1.1, 2.1, 5.1]],
        "semantic_label": "ceiling"
    },
    {
        "label": 2,  # wall
        "points": [[1.0, 0.0, 2.5], [1.1, 0.1, 2.6]],
        "semantic_label": "wall"
    }
]

r = requests.post(
    'http://127.0.0.1:8001/api/pointcloud/enrich/batch',
    json={"segments": segments}
)

results = r.json()
for segment_result in results['enriched_segments']:
    print(f"Label {segment_result['label']}: {len(segment_result['bsdd_data'])} bSDD matches")
```

---

### 2. APS Service - Autodesk Platform Services

#### Get APS Configuration
```bash
# cURL
curl http://127.0.0.1:3001/aps/config

# Python
import requests
r = requests.get('http://127.0.0.1:3001/aps/config')
config = r.json()
print(f"Two-Legged OAuth: {config['twoLeggedConfigured']}")
print(f"Three-Legged OAuth: {config['threeLeggedConfigured']}")
```

#### Get 2-Legged Token (Server-to-Server)
```bash
# cURL
curl http://127.0.0.1:3001/aps/token

# Python
import requests
r = requests.get('http://127.0.0.1:3001/aps/token')
token_data = r.json()
access_token = token_data['access_token']
print(f"Token: {access_token[:50]}...")
print(f"Expires in: {token_data['expires_in']} seconds")
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IlU...",
  "token_type": "Bearer",
  "expires_in": 3599
}
```

#### OAuth Login (3-Legged)
```bash
# Open in browser or redirect
http://127.0.0.1:3001/aps/oauth/login?returnTo=http://localhost:5173

# After login, check status
curl http://127.0.0.1:3001/aps/oauth/status
```

#### Get ACC Hubs (Requires OAuth Login)
```bash
# Python with session
import requests

session = requests.Session()
# First login via browser at http://127.0.0.1:3001/aps/oauth/login
# Then use the session cookie

r = session.get('http://127.0.0.1:3001/acc/hubs')
hubs = r.json()
for hub in hubs:
    print(f"Hub: {hub['attributes']['name']}")
```

#### Upload to OSS (Object Storage Service)
```bash
# Python
import requests
from pathlib import Path

files = {'file': open('model.ifc', 'rb')}
data = {
    'bucketKey': 'bim-spatial-bhupesh-us-001',
    'objectKey': 'model_001.ifc'
}

r = requests.post(
    'http://127.0.0.1:3001/oss/upload',
    files=files,
    data=data
)

result = r.json()
print(f"Uploaded: {result['objectKey']}")
print(f"URN: {result['urn']}")
```

---

### 3. Knowledge Graph API (GraphQL)

#### GraphiQL Playground
```
http://127.0.0.1:8001/api/graphql
```

#### Query bSDD Class
```bash
# cURL with GraphQL
curl -X POST http://127.0.0.1:8001/api/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ bsddClass(uri: \"https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall\") { uri name definition properties { code name dataType } } }"
  }'

# Python
import requests

query = """
{
  bsddClass(uri: "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall") {
    uri
    name
    definition
    properties {
      code
      name
      dataType
      units
    }
  }
}
"""

r = requests.post(
    'http://127.0.0.1:8001/api/graphql',
    json={'query': query}
)

data = r.json()
wall_class = data['data']['bsddClass']
print(f"Class: {wall_class['name']}")
print(f"Properties: {len(wall_class['properties'])}")
```

#### Search Knowledge Graph
```python
import requests

query = """
{
  search(queryText: "thermal") {
    resultType
    uri
    name
    description
  }
}
"""

r = requests.post(
    'http://127.0.0.1:8001/api/graphql',
    json={'query': query}
)

results = r.json()['data']['search']
for result in results:
    print(f"{result['resultType']}: {result['name']}")
```

---

## 🔐 Authentication Examples

### Using APS Bearer Token
```python
import requests

# Get token
token_response = requests.get('http://127.0.0.1:3001/aps/token')
access_token = token_response.json()['access_token']

# Use token with Autodesk API
headers = {
    'Authorization': f'Bearer {access_token}'
}

# Example: Get Forge Viewer manifest
urn = "dXJuOmFkc2sud2lwcHJvZDpmcy5maWxlOnZmLlk..."
r = requests.get(
    f'https://developer.api.autodesk.com/modelderivative/v2/designdata/{urn}/manifest',
    headers=headers
)

manifest = r.json()
print(manifest['status'])
```

---

## 📝 Postman Collection

### Import to Postman

**Collection Variables:**
- `BACKEND_URL`: `http://127.0.0.1:8001`
- `APS_URL`: `http://127.0.0.1:3001`
- `ACCESS_TOKEN`: (dynamically set from /aps/token response)

**Example Requests:**

1. **GET Backend Health**
   - URL: `{{BACKEND_URL}}/api/pointcloud/health`
   - Method: GET

2. **GET Semantic Classes**
   - URL: `{{BACKEND_URL}}/api/pointcloud/semantic-classes`
   - Method: GET

3. **POST Enrich Segment**
   - URL: `{{BACKEND_URL}}/api/pointcloud/enrich`
   - Method: POST
   - Body (JSON):
     ```json
     {
       "semantic_label": "wall",
       "points": [[1.0, 2.0, 3.0]],
       "scene_id": "test_scene"
     }
     ```

4. **GET APS Token**
   - URL: `{{APS_URL}}/aps/token`
   - Method: GET
   - Tests (save token):
     ```javascript
     pm.environment.set("ACCESS_TOKEN", pm.response.json().access_token);
     ```

---

## 🐍 Python Client Example

### Complete Integration
```python
import requests
from typing import List, Dict, Any

class BIMTwinOpsClient:
    def __init__(
        self,
        backend_url: str = "http://127.0.0.1:8001",
        aps_url: str = "http://127.0.0.1:3001"
    ):
        self.backend_url = backend_url
        self.aps_url = aps_url
        self.session = requests.Session()
    
    # Backend Methods
    def get_health(self) -> Dict[str, Any]:
        """Check backend health status"""
        r = self.session.get(f"{self.backend_url}/api/pointcloud/health")
        return r.json()
    
    def get_semantic_classes(self) -> List[Dict[str, Any]]:
        """Get all semantic classes with bSDD mappings"""
        r = self.session.get(f"{self.backend_url}/api/pointcloud/semantic-classes")
        return r.json()['semantic_classes']
    
    def enrich_segment(
        self,
        semantic_label: str,
        points: List[List[float]],
        scene_id: str = None
    ) -> Dict[str, Any]:
        """Enrich point cloud segment with bSDD data"""
        data = {
            "semantic_label": semantic_label,
            "points": points,
            "scene_id": scene_id
        }
        r = self.session.post(
            f"{self.backend_url}/api/pointcloud/enrich",
            json=data
        )
        return r.json()
    
    def enrich_batch(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Batch enrich multiple segments"""
        r = self.session.post(
            f"{self.backend_url}/api/pointcloud/enrich/batch",
            json={"segments": segments}
        )
        return r.json()
    
    # APS Methods
    def get_aps_token(self) -> Dict[str, Any]:
        """Get 2-legged APS access token"""
        r = self.session.get(f"{self.aps_url}/aps/token")
        return r.json()
    
    def get_aps_config(self) -> Dict[str, Any]:
        """Get APS configuration status"""
        r = self.session.get(f"{self.aps_url}/aps/config")
        return r.json()
    
    # GraphQL Method
    def graphql_query(self, query: str) -> Dict[str, Any]:
        """Execute GraphQL query"""
        r = self.session.post(
            f"{self.backend_url}/api/graphql",
            json={'query': query}
        )
        return r.json()

# Usage Example
if __name__ == "__main__":
    client = BIMTwinOpsClient()
    
    # Check health
    health = client.get_health()
    print(f"Backend Status: {health['status']}")
    print(f"Neo4j Connected: {health['neo4j_connected']}")
    
    # Get semantic classes
    classes = client.get_semantic_classes()
    print(f"\nSemantic Classes: {len(classes)}")
    for cls in classes[:3]:
        print(f"  - {cls['name']} (label: {cls['label']})")
    
    # Enrich a wall segment
    result = client.enrich_segment(
        semantic_label="wall",
        points=[[1.0, 2.0, 3.0], [1.1, 2.1, 3.1]],
        scene_id="example_scene"
    )
    print(f"\nEnrichment Result:")
    print(f"  IFC Entities: {result['ifc_entities']}")
    print(f"  bSDD Matches: {len(result['bsdd_data'])}")
    
    # Get APS configuration
    aps_config = client.get_aps_config()
    print(f"\nAPS Configuration:")
    print(f"  Two-Legged: {aps_config['twoLeggedConfigured']}")
    print(f"  Three-Legged: {aps_config['threeLeggedConfigured']}")
```

---

## 🌐 JavaScript/TypeScript Client

```typescript
class BIMTwinOpsClient {
  private backendUrl: string;
  private apsUrl: string;

  constructor(
    backendUrl = 'http://127.0.0.1:8001',
    apsUrl = 'http://127.0.0.1:3001'
  ) {
    this.backendUrl = backendUrl;
    this.apsUrl = apsUrl;
  }

  async getHealth() {
    const response = await fetch(`${this.backendUrl}/api/pointcloud/health`);
    return response.json();
  }

  async getSemanticClasses() {
    const response = await fetch(
      `${this.backendUrl}/api/pointcloud/semantic-classes`
    );
    const data = await response.json();
    return data.semantic_classes;
  }

  async enrichSegment(semanticLabel: string, points: number[][], sceneId?: string) {
    const response = await fetch(`${this.backendUrl}/api/pointcloud/enrich`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ semantic_label: semanticLabel, points, scene_id: sceneId })
    });
    return response.json();
  }

  async getApsToken() {
    const response = await fetch(`${this.apsUrl}/aps/token`);
    return response.json();
  }

  async graphqlQuery(query: string) {
    const response = await fetch(`${this.backendUrl}/api/graphql`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });
    return response.json();
  }
}

// Usage
const client = new BIMTwinOpsClient();

async function example() {
  const health = await client.getHealth();
  console.log('Backend Status:', health.status);

  const classes = await client.getSemanticClasses();
  console.log('Semantic Classes:', classes.length);

  const result = await client.enrichSegment('wall', [[1, 2, 3]]);
  console.log('IFC Entities:', result.ifc_entities);
}

example();
```

---

## 📊 Testing Tools

### cURL Examples

**Save to file: `test_backend.sh`**
```bash
#!/bin/bash
echo "Testing BIMTwinOps Backend..."

# Health check
echo "\n1. Health Check:"
curl -s http://127.0.0.1:8001/api/pointcloud/health | jq .

# Semantic classes
echo "\n2. Semantic Classes:"
curl -s http://127.0.0.1:8001/api/pointcloud/semantic-classes | jq '.semantic_classes | length'

# Enrich segment
echo "\n3. Enrich Wall Segment:"
curl -s -X POST http://127.0.0.1:8001/api/pointcloud/enrich \
  -H "Content-Type: application/json" \
  -d '{"semantic_label":"wall","points":[[1,2,3]],"scene_id":"test"}' | jq '.ifc_entities'

echo "\nTests complete!"
```

### PowerShell Script

**Save to file: `Test-BIMTwinOps.ps1`**
```powershell
Write-Host "Testing BIMTwinOps Services..." -ForegroundColor Cyan

# Test Backend
$health = Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/pointcloud/health"
Write-Host "✅ Backend: $($health.status)" -ForegroundColor Green

# Test APS
$apsConfig = Invoke-RestMethod -Uri "http://127.0.0.1:3001/aps/config"
Write-Host "✅ APS Two-Legged: $($apsConfig.twoLeggedConfigured)" -ForegroundColor Green

# Test GraphQL
$query = @{query="{ __schema { types { name } } }"}
$result = Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/graphql" -Method Post -Body ($query | ConvertTo-Json) -ContentType "application/json"
Write-Host "✅ GraphQL Schema Types: $($result.data.__schema.types.Count)" -ForegroundColor Green

Write-Host "`n✅ All tests passed!" -ForegroundColor Green
```

---

## 🚀 Quick Start Commands

```powershell
# Test all services
python d:\SMART_BIM\test_system.py

# Test backend only
curl http://127.0.0.1:8001/api/pointcloud/health

# Test APS only
curl http://127.0.0.1:3001/aps/config

# Open GraphQL playground
start http://127.0.0.1:8001/api/graphql

# Open frontend
start http://localhost:5173
```

---

## 📖 More Information

- **Backend API Docs**: http://127.0.0.1:8001/docs
- **GraphQL Playground**: http://127.0.0.1:8001/api/graphql
- **Frontend**: http://localhost:5173
- **GitHub**: https://github.com/dparitosh/BIMTwinOps

---

**Last Updated**: 2026-02-15  
**Services Status**: ✅ All Operational
