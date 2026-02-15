# UI/UX Integration Plan: Point Cloud Semantic Enrichment

**Status**: Backend Complete ✅ | Frontend Not Integrated ❌  
**Date**: February 15, 2026  
**Goal**: Connect frontend to Point Cloud Semantic API and display bSDD enrichment

---

## Current Architecture Gap

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Port 5173)                         │
│  ┌──────────────────┐        ┌──────────────────────────────────┐  │
│  │ PointCloudViewer │   ❌   │  No bSDD Enrichment Display     │  │
│  │ (Three.js)       │        │  - No IFC entities              │  │
│  │                  │        │  - No bSDD properties           │  │
│  └──────────────────┘        │  - No confidence scores         │  │
│           │                  └──────────────────────────────────┘  │
│           │ api.jsx                                                │
│           │ uploadPointCloud()                                     │
│           │ chatWithScene()                                        │
│           │ ❌ NO enrichment functions                             │
│           │                                                        │
└───────────┼────────────────────────────────────────────────────────┘
            │
            │ ❌ Configured for port 8000 (MISMATCH!)
            │
┌───────────┼────────────────────────────────────────────────────────┐
│           ▼                                                        │
│     BACKEND (Port 8001) ✅                                         │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ Point Cloud Semantic API                                   │   │
│  │ - POST /api/pointcloud/enrich          ✅ Working          │   │
│  │ - POST /api/pointcloud/enrich/batch    ✅ Working          │   │
│  │ - GET  /api/pointcloud/semantic-classes ✅ Working         │   │
│  │ - GET  /api/pointcloud/health          ✅ Working          │   │
│  └────────────────────────────────────────────────────────────┘   │
│                           │                                        │
│                           ▼                                        │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ Neo4j Knowledge Graph                                      │   │
│  │ - 2,163 bSDD Classes (IFC 4.3)          ✅ Loaded          │   │
│  │ - 56 MAPS_TO relationships              ✅ Created         │   │
│  │ - 92.3% semantic coverage               ✅ Verified        │   │
│  └────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Fix Port Configuration (5 minutes)

### Task 1.1: Update Frontend .env

**File**: `pointcloud-frontend/.env`

**Change**:
```diff
- VITE_BACKEND_API_URL=http://127.0.0.1:8000
+ VITE_BACKEND_API_URL=http://127.0.0.1:8001
```

**Verification**:
```powershell
# Restart Vite dev server
cd pointcloud-frontend
npm run dev
```

---

## Phase 2: Add API Client Functions (15 minutes)

### Task 2.1: Extend api.jsx

**File**: `pointcloud-frontend/src/api.jsx`

**Add Functions**:
```javascript
/**
 * Get all semantic classes with bSDD mappings
 */
export async function getSemanticClasses() {
  const res = await axios.get(`${API_URL}/api/pointcloud/semantic-classes`, {
    timeout: 10000,
  });
  return res.data;
}

/**
 * Enrich a single point cloud segment with bSDD data
 * @param {number} semanticLabel - 0-12 (ceiling, floor, wall, etc.)
 * @param {Array<Array<number>>} points - Point coordinates [[x,y,z], ...]
 * @param {string} sceneId - Optional scene identifier
 */
export async function enrichSegment(semanticLabel, points, sceneId = null) {
  const payload = {
    semantic_label: semanticLabel,
    points: points,
    scene_id: sceneId,
  };
  const res = await axios.post(`${API_URL}/api/pointcloud/enrich`, payload, {
    headers: { "Content-Type": "application/json" },
    timeout: 30000,
  });
  return res.data;
}

/**
 * Enrich multiple segments in batch
 * @param {Array<Object>} segments - [{id, semantic_label, points}, ...]
 */
export async function enrichBatch(segments) {
  const payload = { segments };
  const res = await axios.post(`${API_URL}/api/pointcloud/enrich/batch`, payload, {
    headers: { "Content-Type": "application/json" },
    timeout: 60000,
  });
  return res.data;
}

/**
 * Check Point Cloud Semantic API health
 */
export async function checkPointCloudHealth() {
  const res = await axios.get(`${API_URL}/api/pointcloud/health`, {
    timeout: 5000,
  });
  return res.data;
}
```

**Expected Response Examples**:

**`getSemanticClasses()`**:
```json
{
  "semantic_classes": [
    {
      "id": 0,
      "name": "ceiling",
      "bsdd_classes": [{"uri": "...", "code": "IfcCovering", "name": "Covering"}]
    },
    {
      "id": 2,
      "name": "wall",
      "bsdd_classes": [
        {"uri": "...", "code": "IfcWall", "name": "Wall"},
        {"uri": "...", "code": "IfcWallSTANDARD", "name": "Wall (Standard)"}
      ]
    }
  ],
  "total": 12
}
```

**`enrichSegment(2, wallPoints, "scene1")`**:
```json
{
  "segment_id": "scene1_sem_2",
  "semantic_class": "wall",
  "bsdd_classes": [
    {
      "uri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall",
      "code": "IfcWall",
      "name": "Wall",
      "definition": "A wall is a vertical construction that...",
      "synonyms": ["mur", "wand"],
      "properties": [
        {
          "code": "ThermalTransmittance",
          "name": "Thermal Transmittance",
          "dataType": "Real",
          "units": "W/(m²·K)"
        }
      ],
      "relations": [
        {"relationType": "IsEqualTo", "relatedClassUri": "..."}
      ]
    }
  ],
  "ifc_entities": ["IfcWall", "IfcWallSTANDARD", "IfcWallPARAPET"],
  "confidence": 1.0,
  "neo4j_stored": true
}
```

---

## Phase 3: Update UI Components (30 minutes)

### Task 3.1: Add Enrichment Button to App.jsx

**File**: `pointcloud-frontend/src/App.jsx`

**Location**: Inside `PointCloudPanel` component, after scene loads

**Add Button**:
```jsx
{sceneData && (
  <div className="mb-4">
    <button
      onClick={handleEnrichScene}
      disabled={enriching}
      className="tcs-button tcs-button-primary w-full"
    >
      {enriching ? (
        <>⏳ Enriching with bSDD...</>
      ) : (
        <>🔍 Enrich with bSDD Standards</>
      )}
    </button>
  </div>
)}
```

**Add State**:
```jsx
const [enriching, setEnriching] = useState(false);
const [enrichmentData, setEnrichmentData] = useState(null);
```

**Add Handler**:
```jsx
const handleEnrichScene = async () => {
  if (!sceneData) return;
  
  setEnriching(true);
  try {
    // Group points by semantic label
    const segmentMap = {};
    sceneData.points.forEach((point, idx) => {
      const label = sceneData.labels[idx];
      if (!segmentMap[label]) {
        segmentMap[label] = [];
      }
      segmentMap[label].push(point);
    });

    // Prepare batch payload
    const segments = Object.entries(segmentMap).map(([label, points], idx) => ({
      id: `seg_${idx}`,
      semantic_label: parseInt(label),
      points: points.slice(0, 100), // Sample for performance
    }));

    // Call enrichment API
    const result = await enrichBatch(segments);
    setEnrichmentData(result);
    
    console.log('✅ Enrichment complete:', result);
    alert(`✅ Enriched ${result.enriched_count} segments with bSDD data!`);
  } catch (err) {
    console.error('❌ Enrichment failed:', err);
    alert('Failed to enrich segments. Check console for details.');
  } finally {
    setEnriching(false);
  }
};
```

---

### Task 3.2: Display Enrichment Data in Info Panel

**File**: `pointcloud-frontend/src/App.jsx`

**Location**: Inside `PointCloudPanel`, in the "Info Panel" section where segment details are shown

**Current Code** (approximate):
```jsx
{/* Info Panel */}
<div className="glass p-4" style={{ width: '288px', ... }}>
  {selected && (
    <div>
      <h3>Segment Details</h3>
      <div>Label: {selected.label}</div>
      <div>Point Index: {selected.pointIndex}</div>
    </div>
  )}
</div>
```

**Replace With**:
```jsx
{/* Info Panel */}
<div className="glass p-4" style={{ width: '320px', minWidth: '280px', maxWidth: '380px', flexShrink: 0, overflowY: 'auto' }}>
  {selected ? (
    <div>
      {/* Basic Info */}
      <div className="mb-4">
        <h3 className="text-lg font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
          Segment Details
        </h3>
        <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          <div className="mb-1">
            <span style={{ fontWeight: 600 }}>Label:</span> {selected.label}
          </div>
          <div className="mb-1">
            <span style={{ fontWeight: 600 }}>Point Index:</span> {selected.pointIndex}
          </div>
          <div>
            <span style={{ fontWeight: 600 }}>Segment ID:</span> {selected.segmentId}
          </div>
        </div>
      </div>

      {/* bSDD Enrichment Data */}
      {enrichmentData && enrichmentData.enriched_segments && (() => {
        const segmentEnrichment = enrichmentData.enriched_segments.find(
          s => s.semantic_class === getLabelName(selected.label)
        );
        
        if (!segmentEnrichment) return null;
        
        return (
          <div className="border-t pt-4" style={{ borderColor: 'var(--border-color)' }}>
            <h4 className="font-bold mb-3 flex items-center gap-2" style={{ color: 'var(--tcs-blue)', fontSize: '14px' }}>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
              bSDD Standards
            </h4>

            {/* IFC Entities */}
            {segmentEnrichment.ifc_entities && segmentEnrichment.ifc_entities.length > 0 && (
              <div className="mb-4">
                <div className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>
                  IFC ENTITIES ({segmentEnrichment.ifc_entities.length})
                </div>
                <div className="flex flex-wrap gap-1">
                  {segmentEnrichment.ifc_entities.map((entity, idx) => (
                    <span
                      key={idx}
                      className="tcs-badge tcs-badge-primary"
                      style={{ fontSize: '11px' }}
                    >
                      {entity}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* bSDD Classes */}
            {segmentEnrichment.bsdd_classes && segmentEnrichment.bsdd_classes.length > 0 && (
              <div className="mb-4">
                <div className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>
                  bSDD CLASSIFICATIONS ({segmentEnrichment.bsdd_classes.length})
                </div>
                <div className="space-y-3">
                  {segmentEnrichment.bsdd_classes.slice(0, 3).map((bsddClass, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg"
                      style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
                    >
                      <div className="font-semibold mb-1" style={{ fontSize: '13px', color: 'var(--text-primary)' }}>
                        {bsddClass.name}
                      </div>
                      <div className="text-xs mb-2" style={{ color: 'var(--text-secondary)' }}>
                        {bsddClass.code}
                      </div>
                      {bsddClass.definition && (
                        <div className="text-xs" style={{ color: 'var(--text-muted)', lineHeight: '1.4' }}>
                          {bsddClass.definition.substring(0, 120)}
                          {bsddClass.definition.length > 120 && '...'}
                        </div>
                      )}
                      
                      {/* Properties Preview */}
                      {bsddClass.properties && bsddClass.properties.length > 0 && (
                        <div className="mt-2 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
                          <div className="text-xs font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>
                            PROPERTIES ({bsddClass.properties.length})
                          </div>
                          <div className="space-y-1">
                            {bsddClass.properties.slice(0, 2).map((prop, pIdx) => (
                              <div key={pIdx} className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                • {prop.name} <span style={{ color: 'var(--tcs-blue)' }}>({prop.dataType})</span>
                              </div>
                            ))}
                            {bsddClass.properties.length > 2 && (
                              <div className="text-xs" style={{ color: 'var(--tcs-blue)' }}>
                                +{bsddClass.properties.length - 2} more...
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Relations Preview */}
                      {bsddClass.relations && bsddClass.relations.length > 0 && (
                        <div className="mt-2 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
                          <div className="text-xs font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>
                            RELATIONS ({bsddClass.relations.length})
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {bsddClass.relations.slice(0, 3).map((rel, rIdx) => (
                              <span
                                key={rIdx}
                                className="tcs-badge tcs-badge-secondary"
                                style={{ fontSize: '10px' }}
                              >
                                {rel.relationType}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                  {segmentEnrichment.bsdd_classes.length > 3 && (
                    <div className="text-xs text-center" style={{ color: 'var(--tcs-blue)' }}>
                      +{segmentEnrichment.bsdd_classes.length - 3} more classifications
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Confidence Score */}
            {segmentEnrichment.confidence && (
              <div className="p-2 rounded" style={{ background: 'var(--bg-primary)' }}>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  Confidence: <span style={{ color: 'var(--tcs-blue)', fontWeight: 600 }}>
                    {(segmentEnrichment.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            )}
          </div>
        );
      })()}
    </div>
  ) : (
    <div className="text-center" style={{ color: 'var(--text-muted)', padding: '32px 16px' }}>
      <div style={{ fontSize: '13px' }}>Click a segment to view details</div>
    </div>
  )}
</div>
```

**Add Helper Function**:
```jsx
// Map semantic label ID to name
const getLabelName = (labelId) => {
  const labelNames = [
    "ceiling", "floor", "wall", "beam", "column", "window", 
    "door", "chair", "table", "bookcase", "sofa", "board", "clutter"
  ];
  return labelNames[labelId] || `label_${labelId}`;
};
```

---

### Task 3.3: Add Health Check to Dashboard

**File**: `pointcloud-frontend/src/App.jsx`

**Location**: In the header or status bar

**Add State**:
```jsx
const [apiHealth, setApiHealth] = useState(null);

useEffect(() => {
  checkPointCloudHealth()
    .then(health => {
      console.log('✅ API Health:', health);
      setApiHealth(health);
    })
    .catch(err => {
      console.error('❌ API Health check failed:', err);
      setApiHealth({ status: 'error', error: err.message });
    });
}, []);
```

**Display Badge**:
```jsx
{/* In header, after BIMTwinOps title */}
{apiHealth && (
  <span
    className={`tcs-badge ${apiHealth.neo4j_connected ? 'tcs-badge-success' : 'tcs-badge-error'}`}
    title={`Neo4j: ${apiHealth.neo4j_connected ? 'Connected' : 'Disconnected'} | Semantic Classes: ${apiHealth.semantic_classes_loaded || 0}`}
  >
    {apiHealth.neo4j_connected ? '✅' : '❌'} Knowledge Graph
  </span>
)}
```

---

## Phase 4: Enhanced Features (Future)

### Feature 4.1: Real-time Enrichment During Segmentation

**Flow**:
1. Upload point cloud → Segmentation
2. **Auto-trigger enrichment** immediately after segmentation
3. Display enriched data alongside point cloud

### Feature 4.2: Property Editor

**UI**:
- Click bSDD property → Open property editor
- Edit value, add notes, set status (proposed/approved/built)
- Save to Neo4j as custom property

### Feature 4.3: Export Enriched IFC

**Button**: "Export as IFC with bSDD Properties"

**Backend Endpoint**: `POST /api/pointcloud/export/ifc`

**Payload**:
```json
{
  "scene_id": "Area_5_office_1_point",
  "enrichment_data": { ... },
  "project_info": { ... }
}
```

**Response**: IFC file with:
- IfcWall, IfcDoor, etc. entities
- bSDD properties attached
- Semantic metadata

### Feature 4.4: Multi-Dictionary Support

**UI**: Dropdown to select classification system
- IFC 4.3 (default)
- Uniclass 2015
- Omniclass
- NL-SfB

**Backend**: Query Neo4j for multi-dictionary mappings

### Feature 4.5: 3D Annotation with bSDD

**Flow**:
1. Click segment in point cloud
2. Show bSDD data in sidebar
3. Add annotation: "This wall is load-bearing (IfcWall, Pset_WallCommon.LoadBearing = TRUE)"
4. Annotation saved to Neo4j with URI reference

---

## Testing Checklist

### Backend Tests (Already Passing ✅)

- [x] Health check
- [x] Get semantic classes
- [x] Enrich single segment
- [x] Enrich batch
- [x] Neo4j integration

### Frontend Tests (To Do ❌)

- [ ] **Phase 1**: Update .env to port 8001
- [ ] **Phase 1**: Restart Vite dev server
- [ ] **Phase 1**: Verify frontend can reach backend
- [ ] **Phase 2**: Add API functions to api.jsx
- [ ] **Phase 2**: Test `getSemanticClasses()` in browser console
- [ ] **Phase 2**: Test `enrichSegment()` with sample data
- [ ] **Phase 3**: Add enrichment button to UI
- [ ] **Phase 3**: Click button → See enrichment data
- [ ] **Phase 3**: Display bSDD data in info panel
- [ ] **Phase 3**: Verify IFC entities shown as badges
- [ ] **Phase 3**: Verify properties/relations displayed

### Integration Tests

- [ ] Upload point cloud → Segmentation → **Enrichment** → Display
- [ ] Click segment → See bSDD data
- [ ] Click different segment → See different bSDD data
- [ ] Health check badge in header shows green

---

## Expected User Experience (After Integration)

### Before (Current State) ❌
```
1. User uploads .npy point cloud
2. PointNet segments into 13 classes
3. User sees colored point cloud
4. Click segment → See: "Label: wall, Point Index: 12345"
5. ❌ No bSDD data
6. ❌ No IFC entities
7. ❌ No standardized properties
```

### After (Integrated State) ✅
```
1. User uploads .npy point cloud
2. PointNet segments into 13 classes
3. ✅ Automatic bSDD enrichment triggered
4. User sees colored point cloud
5. Click segment → See:
   - Label: wall
   - IFC Entities: IfcWall, IfcWallSTANDARD, IfcWallPARAPET
   - bSDD Classifications (12):
     * Wall (IfcWall)
       - Definition: "A wall is a vertical construction..."
       - Properties (23): ThermalTransmittance, FireRating, LoadBearing...
       - Relations: IsEqualTo → BS_Wall, HasPart → IfcWallStandardCase
     * Wall (Standard) (IfcWallSTANDARD)
       - Definition: "Standard wall construction..."
     * Wall (Parapet) (IfcWallPARAPET)
       - Definition: "A low wall along the edge of a roof..."
6. ✅ User can export as IFC with bSDD properties
7. ✅ User can switch classification systems (IFC → Uniclass → Omniclass)
```

---

## Summary

| Phase | Tasks | Effort | Status |
|-------|-------|--------|--------|
| **Phase 1** | Fix port configuration | 5 min | ❌ Not Started |
| **Phase 2** | Add API client functions | 15 min | ❌ Not Started |
| **Phase 3** | Update UI components | 30 min | ❌ Not Started |
| **Phase 4** | Enhanced features (future) | TBD | 🔄 Backlog |

**Total Estimated Time**: 50 minutes for full basic integration

**Blockers**: None (backend is ready)

**Next Step**: Update `.env` file and restart Vite dev server

---

## Quick Start Commands

```powershell
# 1. Update frontend .env
cd d:\SMART_BIM\pointcloud-frontend
# Edit .env: VITE_BACKEND_API_URL=http://127.0.0.1:8001

# 2. Restart frontend
npm run dev

# 3. Open browser
Start-Process "http://localhost:5173"

# 4. Test in browser console
fetch('http://127.0.0.1:8001/api/pointcloud/health')
  .then(r => r.json())
  .then(d => console.log('✅ Backend reachable:', d))
```

---

**Document Version**: 1.0  
**Last Updated**: February 15, 2026  
**Related Docs**: [DATA_LAYER_COMPLETE.md](./DATA_LAYER_COMPLETE.md)
