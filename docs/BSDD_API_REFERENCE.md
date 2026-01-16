# bSDD API Quick Reference

## Official Documentation
- **API Documentation**: https://github.com/buildingSMART/bSDD/blob/master/Documentation/bSDD%20API.md
- **Swagger/OpenAPI**: https://app.swaggerhub.com/apis/buildingSMART/Dictionaries/v1
- **GraphQL Playground**: https://test.bsdd.buildingsmart.org/graphiql
- **Production Manage Portal**: https://manage.bsdd.buildingsmart.org/
- **Production Search Portal**: https://search.bsdd.buildingsmart.org/
- **Test Swagger UI**: https://test.bsdd.buildingsmart.org/swagger/
- **Test Search Portal**: https://search-test.bsdd.buildingsmart.org/
- **Test Manage Portal**: https://manage-test.bsdd.buildingsmart.org/

## Base URLs

### Production
- **REST API**: `https://api.bsdd.buildingsmart.org`
- **GraphQL (Secured)**: `https://api.bsdd.buildingsmart.org/graphqls`
- **Identifier URIs**: `https://identifier.buildingsmart.org`

### Test Environment
- **REST API**: `https://test.bsdd.buildingsmart.org`
- **GraphQL**: `https://test.bsdd.buildingsmart.org/graphql`
- **GraphQL (Secured)**: `https://test.bsdd.buildingsmart.org/graphqls`
- **Swagger UI**: `https://test.bsdd.buildingsmart.org/swagger/`
- **Search Portal**: `https://search-test.bsdd.buildingsmart.org/`
- **Manage Portal**: `https://manage-test.bsdd.buildingsmart.org/`

## Authentication

### For Non-Secured APIs
- No authentication required
- Add `User-Agent` header: `"ApplicationName/Version"`
- Example: `"BIMTwinOps/2.0.0"`

### For Secured APIs (GraphQL, Upload, etc.)
- **Azure AD B2C** OAuth2/OpenID Connect
- **Authority**: `https://authentication.buildingsmart.org/tfp/buildingsmartservices.onmicrosoft.com/b2c_1a_signupsignin_c`
- **Tenant**: `buildingsmartservices.onmicrosoft.com`
- **Client ID** (Demo): `4aba821f-d4ff-498b-a462-c2837dbbba70`
- **Scopes**:
  - Production: `https://buildingsmartservices.onmicrosoft.com/bsddapi/read`
  - Test: `https://buildingsmartservices.onmicrosoft.com/api/read`
- **Redirect URI**: Contact bSDD support for production Client ID

## REST API Endpoints (v1)

### Dictionary APIs

#### Get All Dictionaries
```http
GET /api/Dictionary/v1
Query Parameters:
  - Uri (optional): Filter by dictionary URI
  - OrganizationCode (optional): Filter by organization
  - Status (optional): Active, Preview, Inactive
  - LanguageCode (optional): e.g., en-GB, nl-NL
  - IncludeTestDictionaries (optional): true/false
```

#### Get Dictionary with Classes
```http
GET /api/Dictionary/v1/Classes
Query Parameters:
  - Uri (required): Dictionary URI
  - LanguageCode (optional): e.g., en-GB
  - ClassType (optional): Class, GroupOfProperties, AlternativeUse, Material, etc.
  - SearchText (optional): Filter by text
  - RelatedIfcEntities (optional): Filter by IFC entity (e.g., IfcWall)
  - Offset (optional): For pagination
  - Limit (optional): Max 1000
```

#### Get Dictionary with Properties
```http
GET /api/Dictionary/v1/Properties
Query Parameters:
  - Uri (required): Dictionary URI
  - LanguageCode (optional)
  - SearchText (optional)
  - Offset (optional)
  - Limit (optional): Max 1000
```

### Class APIs

#### Get Class Details
```http
GET /api/Class/v1
Query Parameters:
  - Uri (required): Class URI
  - LanguageCode (optional)
  - IncludeChilds (optional): Include child classes
  - IncludeClassProperties (optional): Include properties
  - IncludeClassRelations (optional): Include relations
  - IncludeReverseRelations (optional): Include reverse relations
```

#### Get Class Properties (Paginated)
```http
GET /api/Class/Properties/v1
Query Parameters:
  - Uri (required): Class URI
  - LanguageCode (optional)
  - Offset (optional)
  - Limit (optional): Max 1000
```

#### Get Class Relations (Paginated)
```http
GET /api/Class/Relations/v1
Query Parameters:
  - Uri (required): Class URI
  - LanguageCode (optional)
  - IsReverse (optional): Get reverse relations
  - Offset (optional)
  - Limit (optional): Max 1000
```

### Property APIs

#### Get Property Details
```http
GET /api/Property/v5
Query Parameters:
  - Uri (required): Property URI
  - LanguageCode (optional)
  - IncludeClasses (optional): Include classes using this property
```

#### Get Property Classes (Paginated)
```http
GET /api/Property/Classes/v1
Query Parameters:
  - Uri (required): Property URI
  - LanguageCode (optional)
  - Offset (optional)
  - Limit (optional): Max 1000
```

#### Get Property Relations (Paginated)
```http
GET /api/Property/Relations/v1
Query Parameters:
  - Uri (required): Property URI
  - LanguageCode (optional)
  - IsReverse (optional)
  - Offset (optional)
  - Limit (optional): Max 1000
```

### Search APIs

#### Text Search Across Dictionaries
```http
GET /api/TextSearch/v2
Query Parameters:
  - SearchText (required): Text to search
  - DictionaryUris (optional): Comma-separated URIs
  - LanguageCode (optional)
  - TypeFilter (optional): Class, Property, Material
  - Offset (optional)
  - Limit (optional): Max 100
```

#### Search in Specific Dictionary
```http
GET /api/SearchInDictionary/v1
Query Parameters:
  - DictionaryUri (required)
  - SearchText (optional)
  - LanguageCode (optional)
  - RelatedIfcEntity (optional): e.g., IfcWall
```

#### Class Search
```http
GET /api/Class/Search/v1
Query Parameters:
  - DictionaryUri (required)
  - SearchText (optional)
  - LanguageCode (optional)
  - RelatedIfcEntities (optional): Comma-separated
  - ClassType (optional)
  - Offset (optional)
  - Limit (optional): Max 1000
```

### Lookup Data APIs

#### Get Countries
```http
GET /api/Country/v1
```

#### Get Languages
```http
GET /api/Language/v1
```

#### Get Units
```http
GET /api/Unit/v1
```

#### Get Reference Documents
```http
GET /api/ReferenceDocument/v1
```

### Health Check
```http
GET /api/Health
```

## GraphQL API

### Production Endpoint
```
POST https://api.bsdd.buildingsmart.org/graphqls
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "...",
  "variables": {...}
}
```

### Example Queries

#### Get Dictionaries
```graphql
{
  dictionaries {
    uri
    name
    version
    organizationCodeOwner
    status
    languageCode
    license
    releaseDate
  }
}
```

#### Search Classes in Dictionary
```graphql
query ($dictionaryUri: String!, $searchText: String) {
  dictionary(uri: $dictionaryUri) {
    classSearch(searchText: $searchText) {
      uri
      code
      name
      definition
      classType
      synonyms
      relatedIfcEntityNames
      properties {
        code
        name
        uri
        dataType
        units
      }
    }
  }
}
```

#### Get Class Details
```graphql
query ($dictionaryUri: String!, $classUri: String!) {
  dictionary(uri: $dictionaryUri) {
    class(uri: $classUri, includeChildren: true) {
      uri
      code
      name
      definition
      synonyms
      relatedIfcEntityNames
      properties {
        code
        name
        uri
        description
        dataType
        units
        allowedValues {
          code
          value
        }
      }
      relations {
        relatedClassName
        relatedClassUri
        relationType
      }
      childs {
        uri
        name
      }
    }
  }
}
```

#### Get All Classes with Properties
```graphql
{
  dictionary(uri: "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3") {
    name
    version
    classSearch {
      code
      name
      uri
      definition
      properties {
        code
        name
        dataType
      }
    }
  }
}
```

## Response Formats

### Dictionary Contract
```json
{
  "uri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3",
  "name": "IFC",
  "version": "4.3",
  "organizationCodeOwner": "buildingsmart",
  "status": "Active",
  "languageCode": "en-GB",
  "license": "MIT",
  "releaseDate": "2023-01-01",
  "moreInfoUrl": "https://..."
}
```

### Class Contract
```json
{
  "uri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall",
  "code": "IfcWall",
  "name": "IfcWall",
  "definition": "A wall is a vertical construction...",
  "classType": "Class",
  "synonyms": ["Wall", "Mur"],
  "relatedIfcEntityNames": ["IfcWall"],
  "parentClassReference": {
    "uri": "https://.../IfcBuildingElement",
    "name": "IfcBuildingElement"
  },
  "classProperties": [...],
  "classRelations": [...]
}
```

### Property Contract
```json
{
  "uri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/LoadBearing",
  "code": "LoadBearing",
  "name": "LoadBearing",
  "definition": "Indicates whether the object is intended to carry loads",
  "dataType": "Boolean",
  "units": [],
  "physicalQuantity": null,
  "allowedValues": [
    {"code": "TRUE", "value": "TRUE"},
    {"code": "FALSE", "value": "FALSE"}
  ]
}
```

## URI Patterns

### Dictionary URI
```
https://identifier.buildingsmart.org/uri/{organizationCode}/{code}/{version}
Example: https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3
```

### Class URI
```
https://identifier.buildingsmart.org/uri/{organizationCode}/{code}/{version}/class/{classCode}
Example: https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall
```

### Property URI
```
https://identifier.buildingsmart.org/uri/{organizationCode}/{code}/{version}/prop/{propertyCode}
Example: https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/LoadBearing
```

## Common Query Patterns

### Find IFC Classes for Building Element
```
GET /api/Class/Search/v1?DictionaryUri=https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3&SearchText=wall
```

### Get All Properties for IfcWall
```
GET /api/Class/v1?Uri=https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall&IncludeClassProperties=true
```

### Find All Classes Mapped to IfcWall
```
GET /api/Dictionary/v1/Classes?Uri=<dictionary-uri>&RelatedIfcEntities=IfcWall
```

### Search Across All Dictionaries
```
GET /api/TextSearch/v2?SearchText=thermal+properties&TypeFilter=Property
```

## Rate Limits & Best Practices

1. **User-Agent Header**: Always include `User-Agent: YourApp/Version`
2. **Caching**: Cache dictionary data (24h recommended)
3. **Pagination**: Use Offset/Limit for large result sets
4. **Language**: Specify LanguageCode for consistent results
5. **GraphQL**: Prefer GraphQL for complex queries with multiple relationships
6. **REST**: Use REST for simple lookups and searches

## Error Responses

### 400 Bad Request
```json
{
  "type": "https://tools.ietf.org/html/rfc7231#section-6.5.1",
  "title": "One or more validation errors occurred.",
  "status": 400,
  "errors": {
    "Uri": ["The Uri field is required."]
  }
}
```

### 404 Not Found
```json
{
  "type": "https://tools.ietf.org/html/rfc7231#section-6.5.4",
  "title": "Not Found",
  "status": 404,
  "detail": "Dictionary not found"
}
```

### 204 No Content
Returned when:
- Dictionary hasn't changed since last download date
- No results found for search

## Popular Dictionaries

- **IFC 4.3**: `https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3`
- **IFC 4.0**: `https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.0`
- **Uniclass 2015**: `https://identifier.buildingsmart.org/uri/uniclass/uniclass2015`
- **Omniclass**: `https://identifier.buildingsmart.org/uri/omniclass`
- **NL-SfB 2005**: `https://identifier.buildingsmart.org/uri/nlsfb/nlsfb2005`

## Support & Resources

- **Contact**: bsdd_support@buildingsmart.org
- **Forums**: https://forums.buildingsmart.org/
- **Tech Updates**: https://forums.buildingsmart.org/t/bsdd-tech-updates/4889
- **GitHub**: https://github.com/buildingSMART/bSDD
- **Import Tutorial**: https://github.com/buildingSMART/bSDD/blob/master/Documentation/bSDD%20import%20tutorial.md

## Testing with TEST Environment

### Quick Start with TEST
The TEST environment requires **no authentication** for most APIs, making it perfect for development:

```python
from bsdd_client import BSDDClient

# Initialize with TEST environment
client = BSDDClient(environment="TEST")

# Test dictionary listing
dictionaries = client.get_dictionaries()
print(f"Found {len(dictionaries)} dictionaries")

# Search for IFC classes
results = client.search_classes(
    search_text="wall",
    dictionary_uris=["https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3"]
)
print(f"Found {len(results)} wall classes")

# Get class details
wall_class = client.get_class_details(
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall"
)
print(f"IfcWall has {len(wall_class.properties)} properties")
```

### Interactive Testing
- **Swagger UI**: https://test.bsdd.buildingsmart.org/swagger/
- **GraphQL Playground**: https://test.bsdd.buildingsmart.org/graphiql
- **Search Portal**: https://search-test.bsdd.buildingsmart.org/
- **Manage Portal**: https://manage-test.bsdd.buildingsmart.org/

### Environment Comparison
| Feature | TEST | PRODUCTION |
|---------|------|------------|
| **Purpose** | Development & testing | Production use |
| **Authentication** | Not required for most APIs | Required for GraphQL |
| **Data** | Test/draft dictionaries | Published dictionaries |
| **Swagger UI** | https://test.bsdd.buildingsmart.org/swagger/ | N/A (use SwaggerHub) |
| **GraphQL** | https://test.bsdd.buildingsmart.org/graphql | https://api.bsdd.buildingsmart.org/graphqls |
| **Stability** | May change frequently | Stable releases |

### Switching Environments in Code
```python
# For development/testing
test_client = BSDDClient(environment="TEST")

# For production
prod_client = BSDDClient(environment="PRODUCTION")

# Custom endpoint
custom_client = BSDDClient(
    base_url="https://custom.bsdd.org",
    graphql_url="https://custom.bsdd.org/graphql"
)
```

---

**Note**: This reference is based on bSDD API v1. Check the official documentation for the latest updates and changes.
