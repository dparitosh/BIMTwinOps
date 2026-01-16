# bSDD UI/UX and Data Structure Analysis

## Overview
This document provides a comprehensive analysis of the official bSDD (buildingSMART Data Dictionary) interfaces, components, data structures, and design patterns. This analysis informs our implementation to ensure consistency with the bSDD ecosystem.

## Table of Contents
- [Official Interfaces Analysis](#official-interfaces-analysis)
- [Data Structure Analysis](#data-structure-analysis)
- [UI Component Patterns](#ui-component-patterns)
- [Recommended Implementation](#recommended-implementation)

---

## Official Interfaces Analysis

### 1. bSDD Project Page (https://www.buildingsmart.org/users/services/buildingsmart-data-dictionary/)

**Purpose**: Marketing/overview landing page for bSDD service

**Page Structure**:
```
Header (bSDD branding)
├── Overview Section
├── Embedded Search Widget
├── Popular Dictionaries Showcase
├── Software Integrations
├── Resources Section (Tabbed)
├── FAQ Section
└── Integration Links
```

**UI Components Identified**:
- **Search Widget**:
  - Centered search bar
  - Placeholder examples: "wall", "volume"
  - Instant search suggestion capability
  
- **Dictionary Cards**:
  - Logo/icon display
  - Dictionary name (IFC, ETIM, Uniclass, CCI)
  - Attribution: "by [organization]"
  - Visual grid layout (3-4 columns)
  - "300+ more" call-to-action link
  
- **Software Integration Showcase**:
  - Grid of software logos/cards
  - Featured: Revit plugin, BlenderBIM, usBIM.bSDD, Plannerly
  - "30+ more" expansion link
  
- **Resources Section**:
  - Tab navigation: Basics | Demos | Other
  - Resource links with descriptions:
    * Managing content
    * Data structure
    * Guidelines
    * Referencing in IFC/IDS
    * ISO standards
    * Content verification
  
- **Integration Section**:
  - GitHub repository link
  - API documentation link
  - Tech forum subscription link
  - Contact form
  - Newsletter subscription

**Design Pattern**: Search-first, showcase-heavy, resource-rich landing page with strong visual hierarchy

---

### 2. bSDD Search Page (https://search.bsdd.buildingsmart.org/)

**Purpose**: Primary search interface for bSDD content with advanced filtering

**Page Structure**:
```
Header (Logo + Login/Register)
├── Search Control Panel
│   ├── Main Search Input
│   ├── Search Options Toggle
│   ├── Version/Status Filters
│   └── Type Filters (Icon-based)
├── Dictionaries Browser Section
└── Footer (Copyright + Links)
```

**UI Components Identified**:

1. **Header**:
   - bSDD logo (SVG format)
   - Login/Register button (authentication gate)

2. **Search Controls**:
   ```
   [Search Input Field: "Search the bSDD..."]
   
   Toggle: ☑ Search also in descriptions [i]
   
   Version/Status Filters:
   ☑ Show only the latest version
   ☑ Show only verified content
   ☐ Show preview content
   ☐ Show inactive content
   
   Type Filters (icon-based):
   [🔧 Property] [📦 Class] [🧱 Material] 
   [📁 Group of properties] [📚 Dictionary] [🏢 Organization]
   ```

3. **Dictionaries Section**:
   - "Browse all dictionaries" link
   - Featured dictionary cards: IFC, ETIM, Airport, Uniclass, CCI, OTHER
   - Visual grid layout

4. **Footer**:
   - Copyright © 2026 buildingSMART
   - Links: bSDD | Privacy/Cookie Statement | Terms and Conditions | Tech updates forum
   - "Share feedback" link

**Design Pattern**: Filter-heavy search interface with icon-based type selection, checkbox filters, clean minimalist design

**Key UX Features**:
- Progressive disclosure (show/hide advanced filters)
- Icon-based type selection for quick recognition
- Toggle for expanded search (descriptions)
- Multiple filter dimensions (type, version, status)
- Quick access to popular dictionaries

---

### 3. bSDD Manage Portal (https://manage.bsdd.buildingsmart.org/)

**Purpose**: Dictionary management and upload interface (authentication-gated)

**Page Structure**:
```
Header (bSDD logo)
├── Version Display (v0.7.37)
├── About Link (GitHub docs)
├── Welcome Message
└── Authentication Gate (Login button)
```

**UI Components Identified**:
- **Version Tracking**: Visible version number (v0.7.37)
- **Authentication Gate**: Single "Log in" button
- **Minimal Public Interface**: No preview of functionality before auth
- **Documentation Link**: Direct link to GitHub documentation

**Design Pattern**: Authentication-gated management portal, minimal public interface, version transparency

**Key UX Features**:
- Version transparency (users know which version they're using)
- Simple authentication flow
- Direct link to documentation
- No information overload on landing page

---

### 4. bSDD Tech Updates Forum (https://forums.buildingsmart.org/t/bsdd-tech-updates/4889)

**Purpose**: Technical updates and changelog communication

**Forum Structure**:
```
Thread: "bSDD tech updates" (Pinned)
Category: Developers > bSDD
├── Update Post 1 (with structure)
├── Update Post 2
└── Update Post N
```

**Update Format Pattern**:
```markdown
## Subject: [Clear Heading]
Example: "Slash not dash before version in URI"

### Description
[Detailed explanation of the change]

### Reason
[Why the change is being made]

### When
✅ Already implemented
⏳ Planned for [date]
🔄 In progress

### Transition Plan
[Migration details, backward compatibility, timeline]
```

**UI Components Identified**:
- **Thread Stats**: Views, likes, links, read time
- **Status Emojis**: ✅ (done), ⏳ (planned), 🔄 (in progress)
- **Structured Updates**: Clear sections (What/Why/When/How)
- **Authors**: buildingSMART International staff
- **Tags**: ifc4, ifc2x3, ifc, ifc5, ifc4-errata

**Design Pattern**: Structured changelog format, clear communication, emoji status indicators, detailed transition planning

**Key UX Features**:
- Pinned thread for easy access
- Chronological updates (newest first)
- Clear status indicators
- Detailed transition plans
- Community engagement (likes, replies)

---

### 5. bSDD API Swagger (https://app.swaggerhub.com/apis/buildingSMART/Dictionaries/v1)

**Purpose**: Interactive API documentation and testing

**Features** (standard Swagger UI):
- **API Endpoint List**: Organized by resource type
- **Try-it-out Functionality**: Interactive API testing
- **Schema Contracts**: 40+ schema definitions
- **Request/Response Examples**: JSON format
- **Authentication Info**: API key requirements

**Design Pattern**: Standard Swagger/OpenAPI documentation interface

---

## Data Structure Analysis

### Core Data Model

```
Dictionary (Organization → Dictionary → Version)
├── Classes (1 to many)
│   ├── ClassProperties (many to many with Properties)
│   ├── ClassRelations (relationships between Classes)
│   └── Metadata (codes, definitions, synonyms, etc.)
│
├── Properties (1 to many)
│   ├── AllowedValues (optional enumerations)
│   ├── PropertyRelations (relationships between Properties)
│   └── Metadata (datatype, units, examples, etc.)
│
└── Dictionary Metadata (versioning, licensing, quality assurance)
```

### JSON Import Model Structure

**Dictionary Level**:
```json
{
  "OrganizationCode": "ifc",           // Required, short code
  "DictionaryCode": "ifc",             // Required, short code
  "DictionaryVersion": "4.3",          // Required, semantic versioning
  "LanguageIsoCode": "EN",             // Required, ISO code
  "LanguageOnly": false,               // Required
  "UseOwnUri": false,                  // Required
  "DictionaryUri": "...",              // Required if UseOwnUri=true
  "License": "MIT",                    // Optional, SPDX identifier
  "LicenseUrl": "...",                 // Optional
  "Status": "Active",                  // Preview | Active | Inactive
  "ReleaseDate": "2023-01-01",         // ISO 8601 format
  "QualityAssuranceProcedure": "...",  // Optional
  "Classes": [...],                    // Required, array
  "Properties": [...]                  // Required, array
}
```

**Class Structure**:
```json
{
  "Code": "wall",                      // Required, unique within dictionary
  "Name": "Wall",                      // Required, translatable
  "ClassType": "Class",                // Class | Material | GroupOfProperties | AlternativeUse
  "Definition": "...",                 // Required per ISO, translatable
  "Description": "...",                // Optional, supplementary
  "ParentClassCode": "...",            // Optional, for hierarchy
  "RelatedIfcEntityNamesList": ["IfcWall"],  // Optional, IFC mapping
  "Synonyms": ["Wand", "Mur"],        // Optional, translatable
  "ClassProperties": [...],            // Optional, array
  "ClassRelations": [...]              // Optional, array
}
```

**Property Structure**:
```json
{
  "Code": "height",                    // Required, unique within dictionary
  "Name": "Height",                    // Required, translatable
  "Definition": "...",                 // Required per ISO, translatable
  "DataType": "Real",                  // Required: Boolean | Character | Integer | Real | String | Time
  "Units": ["m", "ft"],                // Optional, array of unit codes
  "Example": "2.5",                    // Optional, translatable
  "PropertyValueKind": "Single",       // Single | Range | List | Complex | ComplexList
  "MinInclusive": 0,                   // Optional, value restriction
  "MaxInclusive": 100,                 // Optional, value restriction
  "AllowedValues": [...]               // Optional, array
}
```

**ClassProperty (Junction)**:
```json
{
  "PropertyCode": "height",            // Required OR PropertyUri
  "PropertyUri": "https://...",        // Required OR PropertyCode
  "PropertySet": "Pset_Common",        // Optional, IFC property set
  "Unit": "m",                         // Optional, single value
  "IsRequired": true,                  // Optional, boolean
  "IsWritable": true,                  // Optional, boolean
  "PredefinedValue": "...",            // Optional
  "MinInclusive": 1.0,                 // Optional, overrides Property
  "MaxInclusive": 5.0,                 // Optional, overrides Property
  "AllowedValues": [...]               // Optional, overrides Property
}
```

**AllowedValue Structure**:
```json
{
  "Code": "REI30",                     // Required, max 20 chars
  "Value": "REI30",                    // Required, translatable
  "Description": "Fire rating 30 min", // Optional, translatable
  "SortNumber": 1                      // Optional
}
```

**Relation Types**:
- **Class Relations**: HasMaterial, HasReference, IsEqualTo, IsSimilarTo, IsParentOf, IsChildOf, HasPart, IsPartOf
- **Property Relations**: HasReference, IsEqualTo, IsSimilarTo, IsParentOf, IsChildOf, HasPart

### Code Format Rules (April 2024)
- **Allowed**: Diacritics, whitespace, dots, commas, dashes, round brackets, underscores, numbers
- **Not allowed**: `" # % / \ : { } [ ] | ; < > ? ~`
- **Case**: Not case-sensitive, small-caps recommended
- **Examples**: "bs-agri", "apple", "éÄą _- (Д開発,...żź)"
- **Reserved**: "Ifc" prefix, "Pset_" prefix (IFC standard)

### URI Format
```
https://identifier.buildingsmart.org/uri/{orgCode}/{dictCode}/{version}/{type}/{code}

Examples:
- Dictionary: https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3
- Class: https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall
- Property: https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/Height
- ClassProperty: https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall/prop/Pset_WallCommon/Height

"latest" version resolution:
https://identifier.buildingsmart.org/uri/bs-agri/fruitvegs/latest/class/fruit
```

### Import Templates

**Dual Format Approach**:
1. **JSON Template**: `bsdd-import-model.json`
   - Programmatic import
   - Full schema definition
   - Machine-readable

2. **Excel Template**: `spreadsheet-import/`
   - User-friendly import
   - Spreadsheet-based data entry
   - Python converter available (`Excel2bSDD_converter.py`)

**Excel Template Sheets**:
```
dictionary.xlsx
├── Sheet: dictionary        (1 row, dictionary metadata)
├── Sheet: class            (N rows, one per class)
├── Sheet: property         (N rows, one per property)
├── Sheet: classproperty    (N rows, class-property junctions)
├── Sheet: classrelation    (N rows, class relationships)
├── Sheet: allowedvalue     (N rows, value enumerations)
└── Sheet: propertyrelation (N rows, property relationships)
```

**Special Fields in Excel**:
- `(Origin Class Code)`: For ClassProperty, links to parent class
- `(Origin Property Code)`: For AllowedValue/PropertyRelation, links to parent property
- `(Origin ClassProperty Code)`: For AllowedValue, links to ClassProperty

---

## UI Component Patterns

### 1. Search Component Pattern

**Key Features**:
```tsx
<SearchComponent>
  <SearchInput 
    placeholder="Search the bSDD..."
    suggestions={true}
    examples={["wall", "volume"]}
  />
  
  <SearchOptions>
    <Toggle label="Search also in descriptions" info={true} />
  </SearchOptions>
  
  <FilterGroup label="Version & Status">
    <Checkbox checked={true}>Show only latest version</Checkbox>
    <Checkbox checked={true}>Show only verified content</Checkbox>
    <Checkbox checked={false}>Show preview content</Checkbox>
    <Checkbox checked={false}>Show inactive content</Checkbox>
  </FilterGroup>
  
  <FilterGroup label="Type">
    <IconFilter icon="🔧" label="Property" />
    <IconFilter icon="📦" label="Class" />
    <IconFilter icon="🧱" label="Material" />
    <IconFilter icon="📁" label="Group of properties" />
    <IconFilter icon="📚" label="Dictionary" />
    <IconFilter icon="🏢" label="Organization" />
  </FilterGroup>
</SearchComponent>
```

**Implementation Recommendation**:
- Use controlled component pattern (React)
- Debounced search input (300-500ms)
- URL state synchronization for shareable searches
- Filter persistence (localStorage)

### 2. Dictionary Card Pattern

**Visual Structure**:
```tsx
<DictionaryCard>
  <Logo src={dictionary.logo} alt={dictionary.name} />
  <Name>{dictionary.name}</Name>
  <Attribution>by {dictionary.organization}</Attribution>
  <Stats>
    <Stat label="Classes">{dictionary.classCount}</Stat>
    <Stat label="Properties">{dictionary.propertyCount}</Stat>
  </Stats>
  <Action href={dictionary.uri}>View Dictionary</Action>
</DictionaryCard>
```

**Design Specs**:
- Card aspect ratio: ~4:3 or square
- Logo: 64x64px or larger
- Grid: 3-4 columns on desktop, 1-2 on mobile
- Hover effect: subtle shadow/scale
- Call-to-action: "300+ more" button for overflow

### 3. Filter Panel Pattern

**Collapsible Sections**:
```tsx
<FilterPanel>
  <FilterSection title="Type" expanded={true}>
    <IconFilterGrid>
      {typeFilters.map(filter => (
        <IconFilter key={filter.id} {...filter} />
      ))}
    </IconFilterGrid>
  </FilterSection>
  
  <FilterSection title="Version & Status" expanded={true}>
    <CheckboxGroup>
      {statusFilters.map(filter => (
        <Checkbox key={filter.id} {...filter} />
      ))}
    </CheckboxGroup>
  </FilterSection>
  
  <FilterSection title="Dictionary" expanded={false}>
    <DictionarySelector multiple={true} />
  </FilterSection>
</FilterPanel>
```

### 4. Update/Changelog Pattern

**Structured Format**:
```tsx
<UpdateCard>
  <UpdateHeader>
    <Subject>{update.subject}</Subject>
    <Status emoji={update.statusEmoji}>{update.status}</Status>
    <Date>{update.date}</Date>
  </UpdateHeader>
  
  <UpdateSection title="Description">
    {update.description}
  </UpdateSection>
  
  <UpdateSection title="Reason">
    {update.reason}
  </UpdateSection>
  
  <UpdateSection title="Transition Plan">
    {update.transitionPlan}
  </UpdateSection>
  
  <UpdateFooter>
    <Author>{update.author}</Author>
    <Reactions likes={update.likes} views={update.views} />
  </UpdateFooter>
</UpdateCard>
```

### 5. Authentication Gate Pattern

**Minimal Landing**:
```tsx
<AuthGate>
  <Logo />
  <Version>Version: {appVersion}</Version>
  <Welcome>Welcome to the bSDD management site</Welcome>
  <LoginButton onClick={handleLogin}>Log in</LoginButton>
  <AboutLink href={docsUrl}>About</AboutLink>
</AuthGate>
```

---

## Recommended Implementation

### Frontend Component Structure

```
src/components/bsdd/
├── search/
│   ├── SearchBar.jsx              (main search input)
│   ├── SearchFilters.jsx          (filter panel)
│   ├── TypeFilter.jsx             (icon-based type selection)
│   └── SearchResults.jsx          (results list/grid)
│
├── dictionary/
│   ├── DictionaryCard.jsx         (dictionary showcase card)
│   ├── DictionaryGrid.jsx         (grid of cards)
│   ├── DictionaryBrowser.jsx      (browsing interface)
│   └── DictionaryDetail.jsx       (detail view)
│
├── class/
│   ├── ClassCard.jsx              (class display)
│   ├── ClassHierarchy.jsx         (tree view)
│   ├── ClassProperties.jsx        (property list)
│   └── ClassRelations.jsx         (relationships)
│
├── property/
│   ├── PropertyCard.jsx           (property display)
│   ├── PropertyValue.jsx          (value display with units)
│   ├── AllowedValues.jsx          (enumeration display)
│   └── PropertyRelations.jsx      (relationships)
│
├── import/
│   ├── ImportForm.jsx             (upload interface)
│   ├── JsonUpload.jsx             (JSON file upload)
│   ├── ExcelUpload.jsx            (Excel file upload)
│   └── ImportValidation.jsx       (validation results)
│
├── common/
│   ├── IconFilter.jsx             (reusable icon filter)
│   ├── CheckboxFilter.jsx         (reusable checkbox filter)
│   ├── StatusBadge.jsx            (status display)
│   ├── VersionDisplay.jsx         (version info)
│   └── AuthGate.jsx               (authentication wrapper)
│
└── updates/
    ├── UpdateCard.jsx             (structured update display)
    ├── UpdateList.jsx             (list of updates)
    └── StatusEmoji.jsx            (emoji status indicator)
```

### Backend Data Model Alignment

**Current Implementation** (from `backend/api/knowledge_graph_schema.py`):
```python
# Node Types
BSDDDictionary
BSDDClass
BSDDProperty
IFCElement
PointCloudSegment
Annotation

# Relationships
BELONGS_TO_DICTIONARY
HAS_PROPERTY
MAPS_TO
HAS_ANNOTATION
HAS_SEGMENT
PART_OF_SEGMENT
```

**Recommended Enhancements** (to match official bSDD model):
```python
# Additional Node Types
BSDDClassProperty      # Junction node for Class-Property relationships
BSDDAllowedValue       # Enumeration values
BSDDClassRelation      # Class relationships
BSDDPropertyRelation   # Property relationships

# Additional Properties
# Dictionary Node
- organizationCode
- dictionaryCode
- dictionaryVersion
- languageIsoCode
- license
- licenseUrl
- status (Preview/Active/Inactive)
- releaseDate
- qualityAssuranceProcedure

# Class Node
- classType (Class/Material/GroupOfProperties/AlternativeUse)
- parentClassCode
- relatedIfcEntityNames (array)
- synonyms (array)
- status

# Property Node
- dataType (Boolean/Character/Integer/Real/String/Time)
- units (array)
- propertyValueKind (Single/Range/List/Complex/ComplexList)
- minInclusive, maxInclusive
- pattern (regex)
- dimension (physical quantity)

# ClassProperty Node (junction)
- propertyCode
- propertySet
- unit (single value)
- isRequired
- isWritable
- predefinedValue
- minInclusive/maxInclusive (overrides)

# Additional Relationships
HAS_PARENT_CLASS       # Class → Class (hierarchy)
RELATED_TO_IFC         # Class → IFCEntity
HAS_SYNONYM            # Class → Synonym
HAS_CLASS_PROPERTY     # Class → ClassProperty → Property
HAS_ALLOWED_VALUE      # Property/ClassProperty → AllowedValue
HAS_CLASS_RELATION     # Class → ClassRelation → Class
HAS_PROPERTY_RELATION  # Property → PropertyRelation → Property
```

### API Endpoints Alignment

**Current REST API** (from `backend/api/kg_routes.py`):
```
GET  /api/kg/dictionaries
GET  /api/kg/dictionaries/{uri}
GET  /api/kg/dictionaries/{uri}/classes
GET  /api/kg/classes/{uri}
GET  /api/kg/properties/{uri}
POST /api/kg/search
GET  /api/kg/stats
```

**Recommended Additions**:
```
# Import/Export
POST   /api/kg/import/json          # Upload JSON import file
POST   /api/kg/import/excel         # Upload Excel template
GET    /api/kg/export/{uri}         # Export dictionary to JSON
POST   /api/kg/validate             # Validate import file

# Class Operations
GET    /api/kg/classes/{uri}/hierarchy   # Get class hierarchy
GET    /api/kg/classes/{uri}/properties  # Get class properties
GET    /api/kg/classes/{uri}/relations   # Get class relations

# Property Operations
GET    /api/kg/properties/{uri}/allowed-values   # Get enumerations
GET    /api/kg/properties/{uri}/relations        # Get property relations

# Management
PUT    /api/kg/dictionaries/{uri}/status         # Activate/deactivate
GET    /api/kg/dictionaries/{uri}/versions       # List versions
POST   /api/kg/dictionaries/{uri}/translate      # Add language
```

### GraphQL Schema Enhancements

**Current Schema** (from `backend/api/kg_graphql.py`):
```graphql
type BsddDictionary
type BsddClass
type BsddProperty
type IfcElement
type PointCloudSegment
```

**Recommended Additions**:
```graphql
type BsddDictionary {
  organizationCode: String!
  dictionaryCode: String!
  version: String!
  languageIsoCode: String!
  status: DictionaryStatus!
  license: String
  licenseUrl: String
  releaseDate: DateTime
  qualityAssuranceProcedure: String
  classes: [BsddClass!]!
  properties: [BsddProperty!]!
  versions: [String!]!              # All versions of this dictionary
}

type BsddClass {
  code: String!
  name: String!
  classType: ClassType!
  definition: String
  description: String
  parentClass: BsddClass              # Hierarchy navigation
  childClasses: [BsddClass!]!
  synonyms: [String!]!
  relatedIfcEntities: [String!]!
  classProperties: [BsddClassProperty!]!
  classRelations: [BsddClassRelation!]!
  status: ResourceStatus!
}

type BsddProperty {
  code: String!
  name: String!
  definition: String
  dataType: DataType!
  units: [String!]!
  propertyValueKind: PropertyValueKind!
  minInclusive: Float
  maxInclusive: Float
  pattern: String
  example: String
  allowedValues: [BsddAllowedValue!]!
  propertyRelations: [BsddPropertyRelation!]!
  status: ResourceStatus!
}

type BsddClassProperty {
  code: String
  property: BsddProperty!
  class: BsddClass!
  propertySet: String
  unit: String
  isRequired: Boolean!
  isWritable: Boolean!
  predefinedValue: String
  minInclusive: Float
  maxInclusive: Float
  allowedValues: [BsddAllowedValue!]!    # Can override property values
}

type BsddAllowedValue {
  code: String!
  value: String!
  description: String
  sortNumber: Int
}

type BsddClassRelation {
  relationType: ClassRelationType!
  relatedClass: BsddClass!
  fraction: Float                        # For HasMaterial relations
}

type BsddPropertyRelation {
  relationType: PropertyRelationType!
  relatedProperty: BsddProperty!
}

enum ClassType {
  CLASS
  MATERIAL
  GROUP_OF_PROPERTIES
  ALTERNATIVE_USE
}

enum DataType {
  BOOLEAN
  CHARACTER
  INTEGER
  REAL
  STRING
  TIME
}

enum PropertyValueKind {
  SINGLE
  RANGE
  LIST
  COMPLEX
  COMPLEX_LIST
}

enum ClassRelationType {
  HAS_MATERIAL
  HAS_REFERENCE
  IS_EQUAL_TO
  IS_SIMILAR_TO
  IS_PARENT_OF
  IS_CHILD_OF
  HAS_PART
  IS_PART_OF
}

enum PropertyRelationType {
  HAS_REFERENCE
  IS_EQUAL_TO
  IS_SIMILAR_TO
  IS_PARENT_OF
  IS_CHILD_OF
  HAS_PART
}

enum DictionaryStatus {
  PREVIEW
  ACTIVE
  INACTIVE
}

enum ResourceStatus {
  ACTIVE
  INACTIVE
}

# Mutations
type Mutation {
  importDictionary(jsonData: String!): ImportResult!
  importDictionaryFromExcel(file: Upload!): ImportResult!
  activateDictionary(uri: String!): BsddDictionary!
  deactivateDictionary(uri: String!): BsddDictionary!
  addLanguage(uri: String!, languageData: String!): BsddDictionary!
}

type ImportResult {
  success: Boolean!
  errors: [String!]!
  warnings: [String!]!
  dictionary: BsddDictionary
}
```

---

## Key Takeaways for Implementation

### 1. **Search-First Design**
- Prominent search bar on all pages
- Advanced filtering (type, version, status, dictionary)
- Icon-based type filters for visual recognition
- Search in descriptions toggle

### 2. **Visual Hierarchy**
- Dictionary showcases (popular first)
- Card-based layouts for browsing
- Clear visual separation of content types
- Status indicators (badges, emojis)

### 3. **Data Structure Alignment**
- Implement ClassProperty junction nodes
- Support AllowedValue enumerations
- Model Class/Property relations properly
- Maintain URI format consistency

### 4. **Import/Export Support**
- Dual format (JSON + Excel)
- Validation before import
- Clear error/warning messages
- Preview before commit

### 5. **Version Management**
- Support multiple versions per dictionary
- "latest" version resolution
- Version status (Preview/Active/Inactive)
- Version comparison tools

### 6. **User Communication**
- Structured update format (What/Why/When/How)
- Status emojis for quick recognition
- Detailed transition plans
- Changelog accessibility

### 7. **Authentication & Authorization**
- Public search/browse (no auth)
- Management portal (auth required)
- Version display for transparency
- Role-based access control

---

## Next Steps

1. **Data Model Enhancement**: Update Neo4j schema to include ClassProperty, AllowedValue, Relations
2. **API Expansion**: Implement import/export endpoints, validation, version management
3. **GraphQL Schema Update**: Add new types and mutations for full bSDD support
4. **Frontend Components**: Build reusable components following official patterns
5. **Import Pipeline**: Support JSON and Excel import with validation
6. **Testing**: Validate against official bSDD test data and examples

---

## References

- [bSDD Project Page](https://www.buildingsmart.org/users/services/buildingsmart-data-dictionary/)
- [bSDD Search Portal](https://search.bsdd.buildingsmart.org/)
- [bSDD Manage Portal](https://manage.bsdd.buildingsmart.org/)
- [bSDD API Documentation](https://app.swaggerhub.com/apis/buildingSMART/Dictionaries/v1)
- [bSDD Tech Updates Forum](https://forums.buildingsmart.org/t/bsdd-tech-updates/4889)
- [bSDD Data Structure Documentation](https://technical.buildingsmart.org/services/bsdd/data-structure/)
- [bSDD JSON Import Model](https://github.com/buildingSMART/bSDD/blob/master/Documentation/bSDD%20JSON%20import%20model.md)
- [bSDD Import Tutorial](https://github.com/buildingSMART/bSDD/blob/master/Documentation/bSDD%20import%20tutorial.md)
- [bSDD GitHub Repository](https://github.com/buildingSMART/bSDD)

---

*Document Version: 1.0*  
*Last Updated: 2025*  
*Status: Complete Analysis*
