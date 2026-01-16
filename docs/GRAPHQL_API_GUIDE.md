# GraphQL API for Knowledge Graph

## Overview
The GraphQL API provides a flexible, efficient way to query the BIMTwinOps knowledge graph. Unlike REST endpoints that require multiple requests, GraphQL allows you to fetch exactly the data you need in a single query.

## Endpoint
- **GraphQL Endpoint**: `http://localhost:8001/api/graphql`
- **GraphiQL UI**: `http://localhost:8001/api/graphql` (Interactive playground in browser)

## Setup

1. **Install Dependencies**
```bash
cd backend/api
pip install strawberry-graphql[fastapi]>=0.246.0
```

2. **Start the Server**
```bash
uvicorn main:app --reload --port 8001
```

3. **Access GraphiQL**
Open your browser to `http://localhost:8001/api/graphql` for an interactive GraphQL playground with:
- Auto-completion
- Documentation explorer
- Query validation
- Result formatting

## Schema Overview

### Node Types
- **BsddDictionary** - buildingSMART Data Dictionary catalogs
- **BsddClass** - Standardized classifications (walls, doors, etc.)
- **BsddProperty** - Standardized properties with data types and units
- **IfcElement** - IFC building elements from BIM models
- **PointCloudSegment** - Segmented point cloud data
- **SearchResult** - Universal search results

### Relationships
GraphQL automatically resolves relationships through field resolvers:
- `BsddClass.properties` - Get all properties for a class
- `BsddClass.relations` - Get related classes
- `BsddProperty.classes` - Get classes using this property
- `IfcElement.bsddMappings` - Get bSDD classifications for IFC element
- `IfcElement.pointCloudSegments` - Get point cloud segments
- `PointCloudSegment.bsddMappings` - Get bSDD classifications

## Query Examples

### 1. Get All bSDD Dictionaries
```graphql
{
  bsddDictionaries(limit: 10) {
    uri
    name
    version
    organizationCode
    status
    languageCode
    releaseDate
  }
}
```

**Response:**
```json
{
  "data": {
    "bsddDictionaries": [
      {
        "uri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3",
        "name": "IFC",
        "version": "4.3",
        "organizationCode": "buildingsmart",
        "status": "Active",
        "languageCode": "en-GB",
        "releaseDate": "2023-01-01"
      }
    ]
  }
}
```

### 2. Get bSDD Class with Properties and Relations
```graphql
{
  bsddClass(uri: "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall") {
    uri
    name
    definition
    classType
    relatedIfcEntities
    synonyms
    
    # Nested query for properties
    properties {
      code
      name
      definition
      dataType
      units
      physicalQuantity
    }
    
    # Nested query for relations
    relations {
      relationType
      relatedClassUri
      relatedClassName
    }
  }
}
```

**Response:**
```json
{
  "data": {
    "bsddClass": {
      "uri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall",
      "name": "IfcWall",
      "definition": "A wall is a vertical construction...",
      "classType": "Class",
      "relatedIfcEntities": ["IfcWall"],
      "synonyms": ["Wall", "Mur"],
      "properties": [
        {
          "code": "LoadBearing",
          "name": "LoadBearing",
          "definition": "Indicates if the wall is load bearing",
          "dataType": "Boolean",
          "units": [],
          "physicalQuantity": null
        },
        {
          "code": "ThermalTransmittance",
          "name": "Thermal Transmittance",
          "definition": "Thermal transmittance coefficient (U-Value)",
          "dataType": "Real",
          "units": ["W/(m²·K)"],
          "physicalQuantity": "ThermalTransmittanceUnit"
        }
      ],
      "relations": [
        {
          "relationType": "IS_SUBCLASS_OF",
          "relatedClassUri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcBuildingElement",
          "relatedClassName": "IfcBuildingElement"
        }
      ]
    }
  }
}
```

### 3. Search bSDD Classes with Filters
```graphql
{
  bsddClasses(
    searchText: "wall",
    classType: "Class",
    ifcEntity: "IfcWall",
    limit: 5
  ) {
    uri
    name
    definition
    relatedIfcEntities
    
    # Get first 3 properties for each class
    properties {
      code
      name
      dataType
    }
  }
}
```

### 4. Get IFC Element with Complete Context
```graphql
{
  ifcElement(globalId: "2O2Fr$t4X7Zf8NOew3FLZA") {
    globalId
    ifcType
    name
    description
    objectType
    
    # Get bSDD standardized classifications
    bsddMappings {
      uri
      name
      definition
      
      # Get standardized properties
      properties {
        code
        name
        definition
        dataType
        units
      }
    }
    
    # Get corresponding point cloud data
    pointCloudSegments {
      segmentId
      semanticLabel
      confidence
      pointCount
      
      # Get bSDD classifications for the segment
      bsddMappings {
        uri
        name
      }
    }
  }
}
```

### 5. Search All Properties for a Class
```graphql
{
  bsddProperties(
    classUri: "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall",
    dataType: "Real",
    limit: 10
  ) {
    uri
    code
    name
    definition
    dataType
    units
    physicalQuantity
    
    # Get all classes using this property
    classes {
      uri
      name
    }
  }
}
```

### 6. Universal Search
```graphql
{
  search(queryText: "thermal", limit: 20) {
    resultType  # "class", "property", "ifc_element", "segment"
    uri
    name
    description
    score
  }
}
```

### 7. Get Knowledge Graph Statistics
```graphql
{
  graphStats {
    totalNodes
    totalRelationships
    bsddDictionariesCount
    bsddClassesCount
    bsddPropertiesCount
    ifcElementsCount
    pointCloudSegmentsCount
    nodeTypeDistribution
  }
}
```

**Response:**
```json
{
  "data": {
    "graphStats": {
      "totalNodes": 15234,
      "totalRelationships": 48756,
      "bsddDictionariesCount": 12,
      "bsddClassesCount": 3450,
      "bsddPropertiesCount": 8920,
      "ifcElementsCount": 2341,
      "pointCloudSegmentsCount": 511,
      "nodeTypeDistribution": {
        "BsddDictionary": 12,
        "BsddClass": 3450,
        "BsddProperty": 8920,
        "IfcElement": 2341,
        "PointCloudSegment": 511
      }
    }
  }
}
```

## Mutation Examples

### 1. Link IFC Element to bSDD Class
```graphql
mutation {
  linkIfcToBsdd(
    ifcGlobalId: "2O2Fr$t4X7Zf8NOew3FLZA",
    bsddClassUri: "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall"
  )
}
```

### 2. Link Point Cloud Segment to bSDD Class
```graphql
mutation {
  linkSegmentToBsdd(
    segmentId: "segment_wall_001",
    bsddClassUri: "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall"
  )
}
```

## Advanced Queries

### Complex Multi-Level Query
```graphql
{
  # Get IFC 4.3 dictionary
  bsddDictionaries(organizationCode: "buildingsmart", limit: 1) {
    uri
    name
    version
  }
  
  # Search for wall-related classes
  wallClasses: bsddClasses(searchText: "wall", limit: 5) {
    uri
    name
    properties {
      code
      name
      dataType
    }
  }
  
  # Get all thermal-related properties
  thermalProps: bsddProperties(searchText: "thermal", limit: 10) {
    uri
    name
    dataType
    units
    classes {
      name
    }
  }
  
  # Get graph statistics
  stats: graphStats {
    bsddClassesCount
    bsddPropertiesCount
  }
}
```

### Pagination Example
```graphql
{
  # Get first 50 classes
  page1: bsddClasses(limit: 50) {
    uri
    name
  }
}

# Then fetch next 50 by filtering
{
  page2: bsddClasses(
    searchText: "",
    limit: 50
    # Note: Offset parameter would need to be added to schema for true pagination
  ) {
    uri
    name
  }
}
```

## Advantages of GraphQL over REST

### REST Approach (Multiple Requests)
```javascript
// 1. Get IFC element
const element = await fetch('/api/ifc/elements/2O2Fr$t4X7Zf8NOew3FLZA');

// 2. Get bSDD mappings (separate request)
const mappings = await fetch(`/api/kg/ifc/${element.globalId}/bsdd-mappings`);

// 3. For each mapping, get properties (N requests!)
for (const mapping of mappings) {
  const props = await fetch(`/api/kg/bsdd/class/${mapping.uri}/properties`);
}

// 4. Get point cloud segments (another request)
const segments = await fetch(`/api/ifc/elements/${element.globalId}/segments`);

// Total: 4 + N requests
```

### GraphQL Approach (Single Request)
```javascript
const query = `
  {
    ifcElement(globalId: "2O2Fr$t4X7Zf8NOew3FLZA") {
      globalId
      name
      bsddMappings {
        uri
        name
        properties {
          code
          name
          dataType
        }
      }
      pointCloudSegments {
        segmentId
        semanticLabel
      }
    }
  }
`;

const response = await fetch('/api/graphql', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query })
});

// Total: 1 request, exactly the data you need
```

## Integration with Frontend

### React Example with Apollo Client
```javascript
import { ApolloClient, InMemoryCache, gql, useQuery } from '@apollo/client';

const client = new ApolloClient({
  uri: 'http://localhost:8001/api/graphql',
  cache: new InMemoryCache(),
});

const GET_WALL_CLASSES = gql`
  query GetWallClasses($searchText: String!) {
    bsddClasses(searchText: $searchText, ifcEntity: "IfcWall") {
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
`;

function WallClassesList() {
  const { loading, error, data } = useQuery(GET_WALL_CLASSES, {
    variables: { searchText: 'wall' }
  });
  
  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  
  return (
    <ul>
      {data.bsddClasses.map(cls => (
        <li key={cls.uri}>
          <h3>{cls.name}</h3>
          <p>{cls.definition}</p>
          <h4>Properties:</h4>
          <ul>
            {cls.properties.map(prop => (
              <li key={prop.code}>
                {prop.name} ({prop.dataType})
                {prop.units.length > 0 && ` - ${prop.units.join(', ')}`}
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
}
```

### Vanilla JavaScript Example
```javascript
async function searchBsddClasses(searchText) {
  const query = `
    query SearchClasses($searchText: String!, $limit: Int) {
      bsddClasses(searchText: $searchText, limit: $limit) {
        uri
        name
        definition
        relatedIfcEntities
        properties {
          code
          name
          dataType
        }
      }
    }
  `;
  
  const response = await fetch('http://localhost:8001/api/graphql', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      variables: { searchText, limit: 10 }
    })
  });
  
  const result = await response.json();
  return result.data.bsddClasses;
}

// Usage
const wallClasses = await searchBsddClasses('wall');
console.log(wallClasses);
```

## GraphiQL Features

The GraphiQL UI at `http://localhost:8001/api/graphql` provides:

1. **Auto-completion**: Press `Ctrl+Space` to see available fields
2. **Documentation Explorer**: Click "Docs" to browse the schema
3. **Query Validation**: Real-time syntax checking
4. **Query History**: Access previous queries
5. **Variable Editor**: Test queries with different variables
6. **Prettify**: Auto-format your queries

## Performance Tips

1. **Request Only What You Need**
   ```graphql
   # Good - Only request needed fields
   { bsddClasses { uri name } }
   
   # Avoid - Fetching all nested data unnecessarily
   { bsddClasses { uri name properties { ... } relations { ... } } }
   ```

2. **Use Fragments for Reusable Fields**
   ```graphql
   fragment ClassBasicInfo on BsddClass {
     uri
     name
     definition
     classType
   }
   
   query {
     wallClasses: bsddClasses(searchText: "wall") {
       ...ClassBasicInfo
     }
     doorClasses: bsddClasses(searchText: "door") {
       ...ClassBasicInfo
     }
   }
   ```

3. **Limit Nested Queries**
   ```graphql
   # Use limits on nested queries
   {
     bsddClass(uri: "...") {
       uri
       name
       properties(limit: 10) {  # Add limit parameter to schema
         code
         name
       }
     }
   }
   ```

## Error Handling

GraphQL returns errors in a standardized format:

```json
{
  "errors": [
    {
      "message": "Class not found",
      "locations": [{ "line": 2, "column": 3 }],
      "path": ["bsddClass"]
    }
  ],
  "data": {
    "bsddClass": null
  }
}
```

## Schema Documentation

The complete schema is available through GraphiQL's documentation explorer. Key types:

- **Query** - Root query type with all read operations
- **Mutation** - Root mutation type for write operations
- **BsddDictionary**, **BsddClass**, **BsddProperty** - bSDD data types
- **IfcElement**, **PointCloudSegment** - Building data types
- **GraphStats** - Statistics type

## Comparison: GraphQL vs REST

| Feature | GraphQL | REST |
|---------|---------|------|
| **Requests** | 1 request | Multiple requests |
| **Over-fetching** | No - get exactly what you need | Yes - fixed endpoints |
| **Under-fetching** | No - fetch nested data in one go | Yes - requires multiple calls |
| **Versioning** | Not needed - add fields | v1, v2, v3 URLs |
| **Documentation** | Auto-generated from schema | Manual Swagger docs |
| **Type Safety** | Built-in with strong types | Requires Pydantic models |
| **Caching** | More complex | Simple HTTP caching |
| **Learning Curve** | Steeper | Gentler |

## Use Cases

**Use GraphQL when:**
- You need complex nested data (IFC element → bSDD mappings → properties)
- Mobile apps with limited bandwidth
- You want to reduce number of requests
- Frontend developers need flexibility

**Use REST when:**
- Simple CRUD operations
- File uploads/downloads
- You need HTTP caching
- Simpler to implement for specific tasks

## Next Steps

1. **Explore GraphiQL**: Open http://localhost:8001/api/graphql
2. **Try Example Queries**: Copy queries from this guide
3. **Integrate with Frontend**: Use Apollo Client or fetch API
4. **Add Custom Queries**: Extend `Query` type in `kg_graphql.py`
5. **Add More Mutations**: Extend `Mutation` type for write operations

## Support

For questions or issues:
- Check GraphiQL documentation explorer
- Review example queries in `kg_graphql.py`
- See [BSDD_INTEGRATION.md](BSDD_INTEGRATION.md) for more context
