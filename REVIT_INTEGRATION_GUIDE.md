# Revit bSDD Plugin Integration - User Guide

## Overview

This guide explains how to use BIMTwinOps to integrate with IFC files exported from Autodesk Revit using the buildingSMART bSDD (Data Dictionary) Plugin. This integration enables powerful workflows for validating as-designed BIM models against as-built point cloud data using standardized building classifications.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Workflow Overview](#workflow-overview)
3. [Step-by-Step Guide](#step-by-step-guide)
4. [API Reference](#api-reference)
5. [Troubleshooting](#troubleshooting)
6. [Advanced Usage](#advanced-usage)

---

## Prerequisites

### Required Software

1. **Autodesk Revit** (2023 or 2024)
2. **bSDD Revit Plugin** (v1.7.4 or later)
   - Download from: https://github.com/buildingsmart-community/bSDD-Revit-plugin/releases
   - Install following the official instructions

3. **BIMTwinOps System**
   - Backend API running on port 8001
   - Frontend running on port 5173
   - Neo4j knowledge graph operational
   - Point cloud semantic service enabled

### Required Knowledge

- Basic understanding of IFC (Industry Foundation Classes)
- Familiarity with buildingSMART Data Dictionary (bSDD)
- Understanding of BIM workflows in Revit

---

## Workflow Overview

### Complete Integration Workflow

```
┌──────────────────┐
│  Revit Model     │
│  + bSDD Plugin   │
└────────┬─────────┘
         │ 1. Classify elements with bSDD
         ▼
┌──────────────────┐
│  IFC Export      │
│  with bSDD refs  │
└────────┬─────────┘
         │ 2. Export IFC with IfcClassificationReference
         ▼
┌──────────────────┐
│  BIMTwinOps      │
│  Upload IFC      │
└────────┬─────────┘
         │ 3. Parse bSDD classifications
         ▼
┌──────────────────┐
│  Neo4j Import    │
│  Knowledge Graph │
└────────┬─────────┘
         │ 4. Store in graph database
         ▼
┌──────────────────┐
│  Validate vs     │
│  Point Cloud     │
└────────┬─────────┘
         │ 5. Compare BIM vs Reality
         ▼
┌──────────────────┐
│  Validation      │
│  Report          │
└──────────────────┘
```

### Key Benefits

✅ **Standardized Classifications**: Use buildingSMART bSDD for consistent element classification  
✅ **As-Built Validation**: Compare design intent (BIM) against reality (point cloud)  
✅ **Quality Control**: Identify discrepancies between model and construction  
✅ **Knowledge Graph**: Build queryable relationships between BIM and point cloud data  
✅ **Audit Trail**: Track which elements have been validated and their accuracy  

---

## Step-by-Step Guide

### Step 1: Classify Elements in Revit

1. **Open your Revit model**

2. **Launch bSDD Plugin**
   - Go to **Add-ins** tab in Revit
   - Click **bSDD Plugin** button
   - The bSDD panel will open on the side

3. **Select Elements to Classify**
   - In Revit, select one or more elements (walls, doors, columns, etc.)
   - The bSDD panel will show available classifications

4. **Search and Apply bSDD Classifications**
   - Use the search bar in bSDD panel
   - Select appropriate dictionary (e.g., "IFC 4.3")
   - Choose the correct classification (e.g., "IfcWall")
   - Click **Apply** to assign the classification

5. **Verify Classifications**
   - Selected elements now have bSDD classification parameters
   - These will be embedded in the IFC export

**Example Classifications:**
- Wall → `IfcWall` or `IfcWallSTANDARD`
- Door → `IfcDoor`
- Column → `IfcColumn`
- Slab → `IfcSlab` or `IfcSlabFLOOR`

### Step 2: Export IFC from Revit

1. **Go to File → Export → IFC**

2. **Configure IFC Export Settings**
   - IFC version: **IFC 4** or **IFC 2x3**
   - File Type: **IFC**
   - Space Boundaries: **2nd Level** (recommended)
   - Base Quantities: **Checked**
   - Split Walls and Columns by Level: **As needed**

3. **Important: bSDD Plugin Post-Processing**
   - The bSDD Plugin automatically post-processes the IFC file
   - It adds `IfcClassificationReference` entities
   - It links classifications to building elements
   - This happens automatically after Revit's standard IFC export

4. **Save IFC File**
   - Choose a descriptive filename (e.g., `ProjectName_Phase1_WithbSDD.ifc`)
   - Note the location for upload to BIMTwinOps

**Expected IFC Structure:**
```ifc
#100 = IFCWALL(...);
#101 = IFCCLASSIFICATIONREFERENCE('https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall','IfcWall','Wall',#102);
#102 = IFCCLASSIFICATION('buildingSMART','4.3',$,'IFC');
#103 = IFCRELASSOCIATESCLASSIFICATION(...,(#100),#101);
```

### Step 3: Upload IFC to BIMTwinOps

1. **Open BIMTwinOps Frontend**
   - Navigate to `http://localhost:5173`
   - Click on **Revit Integration** tab in the main navigation

2. **Upload Tab**
   - Click **Choose File** or drag-and-drop your IFC file
   - File must have `.ifc` extension
   - Click **Upload & Parse** button

3. **Wait for Upload**
   - File will be uploaded to BIMTwinOps backend
   - Parse operation starts automatically
   - Progress indicator will show status

**API Endpoint Used:**
```
POST http://localhost:8001/api/revit-integration/upload-ifc
Content-Type: multipart/form-data
```

### Step 4: View Parse Results

After upload completes, you'll see the **Parse** tab with statistics:

**Statistics Displayed:**
- **Total Elements**: All building elements in the IFC file
- **Classified Elements**: Elements with bSDD classifications
- **Classification Coverage**: Percentage of elements classified
- **bSDD Classifications**: Number of buildingSMART bSDD classifications found

**Classifications by Type:**
```
IFC Type                Count
─────────────────────  ─────
IfcWall                  45
IfcDoor                  12
IfcWindow                18
IfcColumn                 8
IfcSlab                  10
```

**Dictionaries Used:**
- buildingSMART IFC 4.3
- Uniclass 2015 (if used)
- Custom dictionaries (if any)

**Warnings/Errors:**
- Non-bSDD URIs found (non-standard classifications)
- Elements without classifications
- Parse errors (if any)

### Step 5: Import to Neo4j Knowledge Graph

1. **Click "Import to Neo4j" button**

2. **Import Options** (automatic):
   - `project_id`: Optional project identifier
   - `merge_existing`: `true` (merge with existing data)

3. **Import Process:**
   - Creates `RevitElement` nodes in Neo4j
   - Creates `BsddClass` nodes for classifications
   - Creates `CLASSIFIED_AS` relationships
   - Links to existing knowledge graph data

4. **View Import Results:**
   - **Imported Count**: Number of classifications imported
   - **Created Nodes**: List of Neo4j node IDs (GlobalIds)
   - **Status**: Success/Failure
   - **Errors**: Any import errors

**Neo4j Graph Structure:**
```cypher
(:RevitElement {globalId, name, ifcType, projectId})
  -[:CLASSIFIED_AS]->
(:BsddClass {uri, code, name, dictionary})
  -[:MAPS_TO]->
(:SemanticClass {label, classId})
```

**Example Query:**
```cypher
MATCH (re:RevitElement)-[:CLASSIFIED_AS]->(bc:BsddClass)
WHERE re.ifcType = 'IfcWall'
RETURN re.name, bc.code, bc.name
```

### Step 6: Validate Against Point Cloud

1. **Click "Validate vs Point Cloud" button**

2. **Validation Process:**
   - Compares BIM element classifications with point cloud segments
   - Uses spatial matching (bounding box overlap)
   - Checks semantic label agreement
   - Calculates confidence scores

3. **View Validation Results:**

**Overall Statistics:**
- **Matches**: BIM and Point Cloud classifications agree
- **Mismatches**: Classifications differ
- **Missing in PC**: BIM elements not found in point cloud
- **Overall Accuracy**: Percentage of matches

**Detailed Results Table:**
```
Element     BIM Class         PC Class    Status      Confidence
─────────  ───────────────   ──────────  ──────────  ──────────
IfcWall    IfcWallSTANDARD   wall        MATCH       95%
IfcDoor    IfcDoor           door        MATCH       88%
IfcWall    IfcWall           ceiling     MISMATCH    72%
IfcColumn  IfcColumn         N/A         MISSING_PC  0%
```

**Status Types:**
- **MATCH** ✅: BIM and point cloud classifications agree
- **MISMATCH** ⚠️: Classifications differ (potential error)
- **MISSING_PC** ℹ️: Element not found in point cloud data
- **MISSING_BIM** ℹ️: Point cloud segment without BIM element

### Step 7: Analyze and Act on Results

**For MATCH Results:**
- ✅ Quality construction - as-built matches design
- ✅ No action needed
- ✅ Update project documentation with validation

**For MISMATCH Results:**
- ⚠️ Investigate discrepancy
- ⚠️ Possible construction error
- ⚠️ Possible classification error in BIM
- ⚠️ Update model or document deviation

**For MISSING_PC Results:**
- ℹ️ Element not yet constructed
- ℹ️ Element outside point cloud scan area
- ℹ️ Schedule additional scan
- ℹ️ Mark as pending validation

---

## API Reference

### Upload IFC File

**Endpoint:** `POST /api/revit-integration/upload-ifc`

**Request:**
```bash
curl -X POST http://localhost:8001/api/revit-integration/upload-ifc \
  -F "file=@YourProject.ifc" \
  -F "project_id=PROJECT_001"
```

**Response:**
```json
{
  "file_id": "20260216_143022_YourProject.ifc",
  "file_name": "YourProject.ifc",
  "file_size": 2457600,
  "uploaded_at": "2026-02-16T14:30:22.123456",
  "status": "success",
  "message": "File uploaded successfully: YourProject.ifc"
}
```

### Parse IFC File

**Endpoint:** `GET /api/revit-integration/parse-ifc/{file_id}`

**Request:**
```bash
curl http://localhost:8001/api/revit-integration/parse-ifc/20260216_143022_YourProject.ifc
```

**Response:**
```json
{
  "file_name": "YourProject.ifc",
  "ifc_schema": "IFC4",
  "total_elements": 150,
  "classified_elements": 120,
  "classification_coverage": 80.0,
  "dictionaries_used": ["buildingSMART IFC 4.3"],
  "classifications_by_type": {
    "IfcWall": 45,
    "IfcDoor": 12,
    "IfcWindow": 18,
    "IfcColumn": 8,
    "IfcSlab": 10,
    "IfcBeam": 15,
    "IfcRoof": 12
  },
  "bsdd_classifications": 120,
  "errors": [],
  "warnings": ["Non-bSDD URI found: http://example.com/custom/class"]
}
```

### Import to Neo4j

**Endpoint:** `POST /api/revit-integration/import-to-neo4j`

**Request:**
```bash
curl -X POST http://localhost:8001/api/revit-integration/import-to-neo4j \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "20260216_143022_YourProject.ifc",
    "project_id": "PROJECT_001",
    "merge_existing": true
  }'
```

**Response:**
```json
{
  "file_name": "YourProject.ifc",
  "imported_count": 120,
  "created_nodes": [
    "2MF28NhmPCwBEM6rYLBQp1",
    "3J9k2P3m99kBbL6QvYxWp2",
    "..."
  ],
  "errors": [],
  "warnings": [],
  "status": "success"
}
```

### Validate BIM vs Point Cloud

**Endpoint:** `POST /api/revit-integration/validate-bim-vs-pointcloud`

**Request:**
```bash
curl -X POST http://localhost:8001/api/revit-integration/validate-bim-vs-pointcloud \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "20260216_143022_YourProject.ifc",
    "point_cloud_segments": [
      {
        "segment_id": "seg_001",
        "semantic_label": "wall",
        "centroid": [10.5, 20.3, 1.2],
        "confidence": 0.95
      }
    ],
    "spatial_tolerance": 0.5
  }'
```

**Response:**
```json
{
  "timestamp": "2026-02-16T14:35:00.000000",
  "ifc_file": "YourProject.ifc",
  "total_bim_elements": 150,
  "match_count": 95,
  "mismatch_count": 15,
  "missing_pc_count": 40,
  "overall_accuracy": 86.4,
  "validation_results": [
    {
      "element_global_id": "2MF28NhmPCwBEM6rYLBQp1",
      "element_name": "Basic Wall:Interior - 150mm",
      "element_type": "IfcWall",
      "bim_classification": "IfcWallSTANDARD",
      "point_cloud_classification": "wall",
      "match_status": "MATCH",
      "confidence": 0.95,
      "spatial_overlap": 0.92,
      "notes": []
    }
  ],
  "errors": [],
  "warnings": []
}
```

### Get Integration Statistics

**Endpoint:** `GET /api/revit-integration/integration-stats?project_id=PROJECT_001`

**Request:**
```bash
curl http://localhost:8001/api/revit-integration/integration-stats?project_id=PROJECT_001
```

**Response:**
```json
{
  "total_revit_elements": 450,
  "unique_bsdd_classes": 18,
  "total_classifications": 450,
  "bsdd_codes_used": [
    "IfcWall",
    "IfcWallSTANDARD",
    "IfcDoor",
    "IfcWindow",
    "IfcColumn",
    "IfcSlab"
  ],
  "ifc_types_present": [
    "IfcWall",
    "IfcDoor",
    "IfcWindow",
    "IfcColumn",
    "IfcSlab",
    "IfcBeam",
    "IfcRoof"
  ]
}
```

### Clear Imports

**Endpoint:** `DELETE /api/revit-integration/clear-imports?project_id=PROJECT_001`

**Request:**
```bash
curl -X DELETE http://localhost:8001/api/revit-integration/clear-imports?project_id=PROJECT_001
```

**Response:**
```json
{
  "status": "success",
  "message": "Cleared Revit imports for project: PROJECT_001"
}
```

---

## Troubleshooting

### Common Issues

#### Issue: "No bSDD classifications found in IFC file"

**Cause:** IFC file exported without bSDD plugin post-processing

**Solution:**
1. Ensure bSDD Revit plugin is installed and enabled
2. Classify elements in Revit before export
3. Verify plugin post-processes IFC after export
4. Check IFC file contains `IfcClassificationReference` entities

#### Issue: "Parse failed: Invalid IFC file"

**Cause:** Corrupted or non-standard IFC file

**Solution:**
1. Re-export from Revit
2. Validate IFC file using IFC validator tool
3. Check IFC schema version (IFC2x3 or IFC4 supported)
4. Ensure file is not truncated during transfer

#### Issue: "Import to Neo4j failed"

**Cause:** Neo4j connection issue or invalid data

**Solution:**
1. Check Neo4j is running: `http://localhost:7474`
2. Verify credentials in `backend/.env`
3. Check backend logs for detailed error
4. Ensure sufficient Neo4j storage space

#### Issue: "Validation shows all MISMATCH"

**Cause:** Classification label mismatch between BIM and point cloud

**Solution:**
1. Verify point cloud semantic labels match IFC types
2. Check spatial alignment between BIM and point cloud
3. Review spatial_tolerance parameter (try increasing)
4. Manually validate a few elements to confirm

#### Issue: "Low classification coverage percentage"

**Cause:** Many elements not classified in Revit

**Solution:**
1. Classify more elements in Revit before export
2. Use bSDD plugin's bulk classification feature
3. Create classification templates for common element types
4. Document intentionally unclassified elements

### Debug Mode

Enable detailed logging:

**Backend:**
```bash
cd d:\SMART_BIM\backend
set LOG_LEVEL=DEBUG
python -m uvicorn api.main:app --host 127.0.0.1 --port 8001 --reload
```

**Check Logs:**
```bash
# View backend logs
tail -f backend/logs/api.log

# Check Neo4j import
curl http://localhost:8001/api/revit-integration/integration-stats

# Health check
curl http://localhost:8001/api/revit-integration/health
```

---

## Advanced Usage

### Batch Processing Multiple IFC Files

```python
import requests
import glob

API_BASE = "http://localhost:8001"

# Upload all IFC files in directory
for ifc_file in glob.glob("*.ifc"):
    with open(ifc_file, 'rb') as f:
        files = {'file': f}
        response = requests.post(
            f"{API_BASE}/api/revit-integration/upload-ifc",
            files=files
        )
        file_id = response.json()['file_id']
        print(f"Uploaded: {ifc_file} -> {file_id}")
        
        # Auto-import each file
        import_response = requests.post(
            f"{API_BASE}/api/revit-integration/import-to-neo4j",
            json={'file_id': file_id, 'merge_existing': True}
        )
        print(f"Imported: {import_response.json()['imported_count']} classifications")
```

### Custom Validation Logic

```python
# Custom spatial matching algorithm
def custom_spatial_match(bim_element, point_cloud_segments):
    """
    Implement custom spatial matching logic
    """
    bim_bbox = bim_element['bounding_box']
    matches = []
    
    for segment in point_cloud_segments:
        pc_bbox = segment['bounding_box']
        overlap = calculate_overlap(bim_bbox, pc_bbox)
        
        if overlap > 0.3:  # 30% overlap threshold
            matches.append({
                'segment': segment,
                'overlap': overlap,
                'classification': segment['semantic_label']
            })
    
    return matches
```

### Neo4j Query Examples

```cypher
// Find all validated walls with high accuracy
MATCH (re:RevitElement {ifcType: 'IfcWall'})-[:CLASSIFIED_AS]->(bc:BsddClass)
WHERE bc.code STARTS WITH 'IfcWall'
RETURN re.name, bc.code, re.globalId

// Find mismatches between BIM and point cloud
MATCH (re:RevitElement)-[:CLASSIFIED_AS]->(bc:BsddClass)
MATCH (re)-[:VALIDATED_AGAINST]->(pc:PointCloudSegment)
WHERE bc.code <> pc.semanticLabel
RETURN re.globalId, bc.code, pc.semanticLabel

// Classification coverage by IFC type
MATCH (re:RevitElement)
OPTIONAL MATCH (re)-[:CLASSIFIED_AS]->(bc:BsddClass)
RETURN re.ifcType, 
       count(re) as total,
       count(bc) as classified,
       (count(bc) * 100.0 / count(re)) as coverage_percent
ORDER BY coverage_percent DESC
```

---

## Best Practices

### 1. Consistent Classification

- Use the same bSDD dictionary across all projects (e.g., IFC 4.3)
- Create classification templates for common element types
- Document classification decisions in project standards

### 2. Regular Validation

- Validate after each construction phase
- Schedule point cloud scans at key milestones
- Compare design vs as-built systematically

### 3. Quality Control

- Review MISMATCH results promptly
- Investigate discrepancies with field teams
- Update BIM model based on validated data

### 4. Data Management

- Use meaningful project_id values
- Archive IFC files with version numbers
- Keep validation reports for audit trail

### 5. Team Training

- Train Revit users on bSDD plugin
- Educate teams on classification standards
- Share validation results with stakeholders

---

## Support and Resources

### Documentation

- [bSDD Revit Plugin GitHub](https://github.com/buildingsmart-community/bSDD-Revit-plugin)
- [buildingSMART bSDD API](https://github.com/buildingSMART/bSDD)
- [BIMTwinOps Compatibility Analysis](BSDD_REVIT_PLUGIN_COMPATIBILITY.md)

### API Documentation

- Revit Integration API: `http://localhost:8001/docs#/Revit%20Integration`
- Point Cloud API: `http://localhost:8001/docs#/Point%20Cloud`
- Knowledge Graph API: `http://localhost:8001/docs#/Knowledge%20Graph`

### Community

- buildingSMART International: https://www.buildingsmart.org/
- bSDD Community: https://buildingsmart.org/users/services/bsdd/
- GitHub Issues: Report bugs and request features

---

**Last Updated:** February 16, 2026  
**Version:** 1.0.0  
**License:** MIT
