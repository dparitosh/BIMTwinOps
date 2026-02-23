import os
import io
import re
import json
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add parent directory to path for pointnet_s3dis import
_backend_dir = Path(__file__).parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import numpy as np
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from neo4j import GraphDatabase, basic_auth

from pointnet_s3dis.online_segmentation import process_uploaded_array

# Centralized config — loads .env and provides all settings
from .config import cfg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import generative UI router
try:
    from .generative_ui.api import router as generative_ui_router
    GENERATIVE_UI_AVAILABLE = True
except ImportError:
    GENERATIVE_UI_AVAILABLE = False
    print("Warning: Generative UI module not available")


# All configuration from centralized config (backend/.env)
GOOGLE_API_KEY = cfg.GOOGLE_API_KEY
NEO4J_URI = cfg.NEO4J_URI
NEO4J_USER = cfg.NEO4J_USER
NEO4J_PASSWORD = cfg.NEO4J_PASSWORD
NEO4J_DATABASE = cfg.NEO4J_DATABASE

# Ollama configuration (local LLM)
OLLAMA_BASE_URL = cfg.OLLAMA_BASE_URL
OLLAMA_MODEL = cfg.OLLAMA_MODEL
OLLAMA_EMBED_MODEL = cfg.OLLAMA_EMBED_MODEL
LLM_PROVIDER = cfg.LLM_PROVIDER

driver = None
if not NEO4J_URI or not NEO4J_USER or not NEO4J_PASSWORD:
    logger.warning("Neo4j is not configured (NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD). Neo4j features will be disabled.")
else:
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD))
    except Exception as e:
        logger.warning("Failed to connect to Neo4j (%s). Neo4j features will be disabled.", e)
        driver = None

 # noqa: E402

MODEL_ENDPOINTS = [
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
    "https://generativelanguage.googleapis.com/v1/models/gemini-2.5:generateContent",
    "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent",
]

DISALLOWED = re.compile(
    r"\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP|CALL|LOAD\s+CSV|FOREACH|APOC|DBMS|ALTER)\b",
    re.I,
)
CODEBLOCK_RE = re.compile(r"```(?:cypher)?\s*([\s\S]*?)```", re.I)

SYSTEM_PROMPT_GEN_CYPHER = (
    "Schema: (:PointCloudSegment {segmentId, sceneId, semanticLabel, centroidPoint, pointCount}).\n"
    "Rules: generate ONE safe READ-ONLY Cypher query only. Use label :PointCloudSegment (never :Segment or :Object). "
    "Use property semanticLabel (never category or semantic_name). Use point.distance(a,b) for distances. "
    "Always include WHERE seg.sceneId = '<SCENE_ID>' when a scene_id is provided.\n\n"
    "Output format (exactly):\n```cypher\n<MATCH ...>\n<RETURN ...>\n```\n\n"
    "If impossible, output exactly:\n```cypher\n# EMPTY\n```\n"
    "After the code block add one short English sentence explanation."
)

SYSTEM_PROMPT_SYNTHESIZE = (
    'You are a concise assistant. Given the user question, the cypher executed and JSON results, '
    'produce a one-line plain English answer. If results are empty, say "No matching results found."'
)

DIST_BETWEEN_RE = re.compile(r"distance.*between\s+([a-z0-9 _-]+)\s+and\s+([a-z0-9 _-]+)", re.I)
WITHIN_RE = re.compile(r"(within|less than|under)\s+([0-9]*\.?[0-9]+)\s*(m|meters|meter)\s+of\s+([a-z0-9 _-]+)", re.I)
COUNT_RE = re.compile(r"(how many|number of|count of)\s+([a-z0-9 _-]+)", re.I)
LIST_RE = re.compile(r"(find|show|list|what are|give me)\s+(?:all|every)?\s*([a-z0-9 _-]+)", re.I)


@asynccontextmanager
async def lifespan(_application: FastAPI):
    """Startup/shutdown lifecycle — ensures Neo4j drivers are closed cleanly."""
    logger.info("BIMTwinOps API starting up")
    yield
    # --- Shutdown ---
    logger.info("BIMTwinOps API shutting down — closing Neo4j drivers")
    if driver is not None:
        try:
            driver.close()
            logger.info("Main Neo4j driver closed")
        except Exception as exc:
            logger.warning("Error closing main Neo4j driver: %s", exc)
    # Close KG-routes singleton drivers (if initialised)
    try:
        from .kg_routes import _kg_schema, _genai_service
        if _kg_schema is not None:
            _kg_schema.close()
            logger.info("KG schema driver closed")
        if _genai_service is not None:
            _genai_service.close()
            logger.info("GenAI service Neo4j driver closed")
    except Exception as exc:
        logger.warning("Error closing kg_routes drivers: %s", exc)
    # kg_graphql now reuses kg_routes singletons — no separate driver to close


app = FastAPI(title="BIMTwinOps API", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=cfg.CORS_METHODS,
    allow_headers=cfg.CORS_HEADERS,
)

# Import and include Knowledge Graph routes
try:
    from .kg_routes import router as kg_router
    app.include_router(kg_router)
    logger.info("Knowledge Graph routes loaded successfully")
except ImportError as e:
    logger.warning(f"Knowledge Graph routes not available: {e}")
except Exception as e:
    logger.error(f"Failed to load Knowledge Graph routes: {e}")

# Import and include GraphQL API
try:
    from .kg_graphql import graphql_router
    app.include_router(graphql_router, prefix="", tags=["GraphQL"])
    logger.info("GraphQL API enabled at /api/graphql (GraphiQL UI available)")
except ImportError as e:
    logger.warning(f"GraphQL API not available: {e}")
except Exception as e:
    logger.error(f"Failed to load GraphQL API: {e}")

# Import and include Generative UI routes
if GENERATIVE_UI_AVAILABLE:
    try:
        app.include_router(generative_ui_router, prefix="/api/ui", tags=["Generative UI"])
        logger.info("Generative UI API enabled at /api/ui")
    except Exception as e:
        logger.error(f"Failed to load Generative UI routes: {e}")

# Import and include HITL approval routes
try:
    from .approvals.api import router as approvals_router
    app.include_router(approvals_router)
    logger.info("Approvals API enabled at /api/approvals")
except Exception as e:
    logger.warning("Approvals API not available: %s", e)

# Import and include Scheduling routes
try:
    from .scheduling.api import router as scheduling_router
    app.include_router(scheduling_router)
    logger.info("Scheduling API enabled at /api/schedules")
except Exception as e:
    logger.warning("Scheduling API not available: %s", e)

# Import and include Point Cloud Semantic routes
try:
    logger.info("Attempting to import pointcloud_semantic module...")
    from .pointcloud_semantic import router as pointcloud_router
    logger.info(f"Successfully imported router with prefix: {pointcloud_router.prefix}")
    logger.info(f"Router has {len(pointcloud_router.routes)} routes")
    app.include_router(pointcloud_router)
    logger.info("Point Cloud Semantic API enabled at /api/pointcloud")
except Exception as e:
    logger.error(f"Point Cloud Semantic API not available: {e}", exc_info=True)

# Import and include Revit bSDD Plugin Integration routes
try:
    logger.info("Attempting to import revit_integration_api module...")
    from .revit_integration_api import router as revit_integration_router
    app.include_router(revit_integration_router)
    logger.info("Revit Integration API enabled at /api/revit-integration")
except Exception as e:
    logger.error(f"Revit Integration API not available: {e}", exc_info=True)


@app.get("/health")
def health():
    """Root health endpoint - checks backend API availability and Neo4j connection"""
    neo4j_connected = False
    if driver is not None:
        try:
            with driver.session(database=NEO4J_DATABASE) as session:
                row = session.run("RETURN 1 AS ok").single()
                neo4j_connected = bool(row and row.get("ok") == 1)
        except Exception:
            neo4j_connected = False
    
    return {
        "status": "healthy",
        "service": "BIMTwinOps API",
        "version": "2.0.0",
        "port": cfg.BACKEND_PORT,
        "neo4j_connected": neo4j_connected,
        "llm_provider": LLM_PROVIDER,
    }


@app.get("/health/neo4j")
def health_neo4j():
    """Basic Neo4j connectivity check (and verifies the selected database exists)."""
    if driver is None:
        raise HTTPException(status_code=503, detail="Neo4j is not configured or not reachable")
    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            row = session.run("RETURN 1 AS ok").single()
        return {"ok": bool(row and row.get("ok") == 1), "database": NEO4J_DATABASE, "uri": NEO4J_URI}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neo4j health check failed: {e}") from e

class ChatReq(BaseModel):
    question: str
    scene_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

@app.post("/upload")
async def upload_pointcloud(file: UploadFile = File(...)):
    # Check file type
    filename = file.filename or "unknown.npy"
    filename_lower = filename.lower()
    if filename_lower.endswith(('.ifc', '.rvt', '.dwg', '.dxf', '.nwd', '.nwc')):
        raise HTTPException(
            status_code=400,
            detail="BIM model files (.ifc, .rvt, etc.) should be uploaded via APS Viewer tab, not PointCloud tab. "
                   "This endpoint accepts .npy point cloud files or text-based coordinate files (CSV/TXT)."
        )
    
    data = await file.read()
    if filename_lower.endswith(".npy"):
        np_array = np.load(io.BytesIO(data))
    else:
        # Try to parse as text coordinates (CSV/TXT)
        try:
            from io import StringIO
            np_array = np.loadtxt(StringIO(data.decode("utf-8")))
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse file as point cloud data. Expected .npy or text coordinates (CSV/TXT). Error: {str(e)}"
            ) from e
    
    scene_id = os.path.splitext(filename)[0]
    try:
        return process_uploaded_array(np_array, scene_id=scene_id)
    except FileNotFoundError as e:
        # PointNet weights are not always present in lightweight installs.
        # Fall back to spatial clustering to create interesting visualizations.
        logger.warning("PointNet weights not found; using spatial clustering fallback: %s", e)
        return fallback_spatial_segmentation(np_array, scene_id, str(e))

def fallback_spatial_segmentation(np_array: np.ndarray, scene_id: str, warning_msg: str):
    """
    Fallback segmentation using spatial clustering when PointNet weights unavailable.
    Creates varied segments based on Z-height and XY grid position.
    """
    xyz = np_array
    if isinstance(xyz, np.ndarray) and xyz.ndim == 2 and xyz.shape[1] >= 3:
        xyz = xyz[:, :3].astype(np.float64)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid point cloud array shape: {getattr(np_array, 'shape', None)}")
    
    n_points = xyz.shape[0]
    
    # Normalize to [0,1] range for easier clustering
    mins = xyz.min(axis=0)
    maxs = xyz.max(axis=0)
    ranges = maxs - mins
    ranges[ranges == 0] = 1  # Avoid division by zero
    xyz_norm = (xyz - mins) / ranges
    
    # Semantic class names from S3DIS
    SEMANTIC_NAMES = [
        "ceiling", "floor", "wall", "beam", "column",
        "window", "door", "chair", "table", "bookcase",
        "sofa", "board", "clutter"
    ]
    
    # Strategy: Assign labels based on height (Z) and XY grid position
    # This creates a varied visualization without ML
    labels = np.zeros(n_points, dtype=np.int64)
    
    # Height-based classification (Z axis)
    z_norm = xyz_norm[:, 2]
    
    # Floor (bottom 5%)
    floor_mask = z_norm < 0.05
    labels[floor_mask] = 1  # floor
    
    # Ceiling (top 5%)
    ceiling_mask = z_norm > 0.95
    labels[ceiling_mask] = 0  # ceiling
    
    # Walls and other objects based on XY position
    middle_mask = ~floor_mask & ~ceiling_mask
    middle_indices = np.where(middle_mask)[0]
    
    if len(middle_indices) > 0:
        # Divide XY plane into a 3x3 grid
        x_norm = xyz_norm[middle_indices, 0]
        y_norm = xyz_norm[middle_indices, 1]
        
        # Edge detection (near boundaries = walls)
        near_x_min = x_norm < 0.1
        near_x_max = x_norm > 0.9
        near_y_min = y_norm < 0.1
        near_y_max = y_norm > 0.9
        
        wall_mask = near_x_min | near_x_max | near_y_min | near_y_max
        
        # Assign walls
        for i, idx in enumerate(middle_indices):
            if wall_mask[i]:
                labels[idx] = 2  # wall
            else:
                # Interior objects based on grid position
                gx = int(min(2, x_norm[i] * 3))
                gy = int(min(2, y_norm[i] * 3))
                grid_cell = gx * 3 + gy
                
                # Map grid cells to furniture classes
                cell_to_class = {
                    0: 7,   # chair
                    1: 8,   # table
                    2: 9,   # bookcase
                    3: 10,  # sofa
                    4: 8,   # table (center)
                    5: 7,   # chair
                    6: 11,  # board
                    7: 9,   # bookcase
                    8: 12,  # clutter
                }
                labels[idx] = cell_to_class.get(grid_cell, 12)
    
    # Build segments
    unique_labels = np.unique(labels)
    segments = []
    
    for lbl in unique_labels:
        mask = labels == lbl
        pts = xyz[mask]
        if len(pts) == 0:
            continue
            
        centroid = pts.mean(axis=0)
        seg_mins = pts.min(axis=0)
        seg_maxs = pts.max(axis=0)
        
        segments.append({
            "segment_key": int(lbl),
            "semantic_id": int(lbl),
            "semantic_name": SEMANTIC_NAMES[lbl] if lbl < len(SEMANTIC_NAMES) else "clutter",
            "centroid": centroid.tolist(),
            "bbox_min": seg_mins.tolist(),
            "bbox_max": seg_maxs.tolist(),
            "num_points": int(np.sum(mask)),
        })
    
    # Build edges (connect adjacent segments)
    edges = []
    for i, s1 in enumerate(segments):
        for j, s2 in enumerate(segments):
            if i >= j:
                continue
            c1 = np.array(s1["centroid"])
            c2 = np.array(s2["centroid"])
            dist = float(np.linalg.norm(c1 - c2))
            if dist < 5.0:  # Only connect nearby segments
                edges.append({
                    "from": s1["segment_key"],
                    "to": s2["segment_key"],
                    "distance": round(dist, 3)
                })
    
    return {
        "scene_id": scene_id,
        "points": xyz.astype(float).tolist(),
        "labels": labels.tolist(),
        "segments": segments,
        "edges": edges,
        "segmentation": "spatial_clustering_fallback",
        "warning": f"Using spatial clustering fallback. {warning_msg}",
    }

def extract_cypher_from_text(text: str) -> Tuple[str, str]:
    m = CODEBLOCK_RE.search(text or "")
    cypher = ""
    if m:
        cypher = m.group(1).strip()
        if cypher.upper().startswith("# EMPTY"):
            cypher = ""
    explanation = re.sub(CODEBLOCK_RE, "", text or "").strip().split("\n")
    explanation_line = ""
    for line in explanation:
        if line.strip():
            explanation_line = line.strip()
            break
    return cypher, explanation_line

def validate_cypher_readonly(cypher: str) -> bool:
    if not cypher:
        return False
    if DISALLOWED.search(cypher):
        return False
    if ";" in cypher.replace("\n", " "):
        return False
    if "RETURN" not in cypher.upper():
        return False
    return True

def normalize_distance_and_sanitize(cypher: str) -> str:
    if not isinstance(cypher, str):
        return ""
    # Unescape literal "\n" sequences
    cy = cypher.replace("\\n", "\n")
    
    # 1. Fix bare 'distance(' -> 'point.distance('
    # The (?<!point\.) prevents matching if 'point.' is already present
    cy = re.sub(r"(?<!point\.)\bdistance\s*\(", "point.distance(", cy, flags=re.I)
    
    # 2. Fix 'point.point.distance' just in case it still occurs
    cy = cy.replace("point.point.distance", "point.distance")
    
    # Remove leading junk and trim
    cy = re.sub(r"^[^\w\(\n\r]*", "", cy)
    cy = cy.strip()
    
    return cy

def neo4j_json(v: Any):
    try:
        if hasattr(v, "x") and hasattr(v, "y"):
            return {"x": float(v.x), "y": float(v.y), "z": float(getattr(v, "z", 0.0))}
        if isinstance(v, dict):
            return {k: neo4j_json(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [neo4j_json(x) for x in v]
        if isinstance(v, (int, float, str, bool)) or v is None:
            return v
        return str(v)
    except Exception:
        return str(v)

def run_cypher_and_serialize(cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    if driver is None:
        raise RuntimeError("Neo4j driver is not available")
    with driver.session(database=NEO4J_DATABASE) as session:
        results = session.run(cypher, parameters=params or {}).data()
    json_rows = []
    for row in results:
        j = {}
        for k, v in row.items():
            j[k] = neo4j_json(v)
        json_rows.append(j)
    return json_rows

def fallback_pattern_cypher(question: str, scene_id: Optional[str]) -> Tuple[str, str, Dict[str, Any]]:
    """Return (cypher, explanation, params) using parameterised queries to prevent injection."""
    q = (question or "").lower()
    params: Dict[str, Any] = {}
    m = DIST_BETWEEN_RE.search(q)
    if m and scene_id:
        a = m.group(1).strip()
        b = m.group(2).strip()
        cy = (
            "MATCH (a:PointCloudSegment {sceneId: $sceneId}), (b:PointCloudSegment {sceneId: $sceneId}) "
            "WHERE toLower(a.semanticLabel) CONTAINS toLower($labelA) AND toLower(b.semanticLabel) CONTAINS toLower($labelB) "
            "RETURN a.segmentId AS a_id, b.segmentId AS b_id, point.distance(a.centroidPoint, b.centroidPoint) AS dist LIMIT 10"
        )
        params = {"sceneId": scene_id, "labelA": a, "labelB": b}
        return cy, f"Distance between {a} and {b}", params
    m2 = WITHIN_RE.search(q)
    if m2 and scene_id:
        meters = float(m2.group(2))
        target = m2.group(4).strip()
        cy = (
            "MATCH (t:PointCloudSegment {sceneId: $sceneId}) "
            "WHERE toLower(t.semanticLabel) CONTAINS toLower($target) "
            "WITH t "
            "MATCH (o:PointCloudSegment {sceneId: $sceneId}) "
            "WHERE o.segmentId <> t.segmentId AND point.distance(t.centroidPoint, o.centroidPoint) <= $meters "
            "RETURN o.segmentId AS id, o.semanticLabel AS semanticLabel, point.distance(t.centroidPoint, o.centroidPoint) AS dist LIMIT 200"
        )
        params = {"sceneId": scene_id, "target": target, "meters": meters}
        return cy, f"Objects within {meters} m of {target}", params
    m3 = COUNT_RE.search(q)
    if m3 and scene_id:
        sem = m3.group(2).strip().split()[0]
        cy = (
            "MATCH (s:PointCloudSegment {sceneId: $sceneId}) "
            "WHERE toLower(s.semanticLabel) CONTAINS toLower($sem) "
            "RETURN count(s) AS count"
        )
        params = {"sceneId": scene_id, "sem": sem}
        return cy, f"Count of {sem}", params
    m4 = LIST_RE.search(q)
    if m4 and scene_id:
        sem = m4.group(2).strip().split()[0]
        cy = (
            "MATCH (s:PointCloudSegment {sceneId: $sceneId}) "
            "WHERE toLower(s.semanticLabel) CONTAINS toLower($sem) "
            "RETURN s.segmentId AS id, s.semanticLabel AS semanticLabel, s.pointCount AS pointCount LIMIT 200"
        )
        params = {"sceneId": scene_id, "sem": sem}
        return cy, f"List segments matching {sem}", params
    return "", "", {}

def call_gemini(system_instruction: str, user_prompt: str, timeout: int = 30) -> str:
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY missing in environment")
    headers = {"Content-Type": "application/json", "x-goog-api-key": GOOGLE_API_KEY}
    merged = (system_instruction.strip() + "\n\n" + user_prompt.strip()).strip()
    body = {"contents": [{"parts": [{"text": merged}]}]}
    last_err: Exception | RuntimeError | None = None
    for url in MODEL_ENDPOINTS:
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=timeout)
            if resp.status_code >= 400:
                last_err = RuntimeError(f"{resp.status_code}: {resp.text}")
                continue
            data = resp.json()
            if "candidates" in data and isinstance(data["candidates"], list) and data["candidates"]:
                cand = data["candidates"][0]
                content = cand.get("content") or cand.get("output") or cand.get("content_parts")
                if isinstance(content, list):
                    parts = []
                    for p in content:
                        if isinstance(p, dict) and "text" in p:
                            parts.append(p["text"])
                        elif isinstance(p, str):
                            parts.append(p)
                    return "\n".join(parts)
                elif isinstance(content, str):
                    return content
            if "output" in data:
                return json.dumps(data["output"], ensure_ascii=False)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Gemini failed: {last_err}") from last_err


def call_ollama(system_instruction: str, user_prompt: str, timeout: int = 60) -> str:
    """Call local Ollama LLM for text generation."""
    url = f"{OLLAMA_BASE_URL}/api/generate"
    merged_prompt = f"{system_instruction.strip()}\n\n{user_prompt.strip()}"
    
    body = {
        "model": OLLAMA_MODEL,
        "prompt": merged_prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 500
        }
    }
    
    try:
        resp = requests.post(url, json=body, timeout=timeout)
        if resp.status_code >= 400:
            raise RuntimeError(f"Ollama error {resp.status_code}: {resp.text}")
        data = resp.json()
        return data.get("response", "")
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. Make sure Ollama is running.") from exc
    except Exception as e:
        raise RuntimeError(f"Ollama failed: {e}") from e


def call_llm(system_instruction: str, user_prompt: str, timeout: int = 60) -> str:
    """Call the configured LLM provider (Ollama or Gemini)."""
    if LLM_PROVIDER == "ollama":
        return call_ollama(system_instruction, user_prompt, timeout)
    elif LLM_PROVIDER == "gemini":
        return call_gemini(system_instruction, user_prompt, timeout)
    else:
        # Default to Ollama
        return call_ollama(system_instruction, user_prompt, timeout)

def synthesize_conversational_reply(question: str, cypher: str, rows: List[Dict[str, Any]]) -> str:
    """
    Ask the LLM to produce a 1-2 sentence conversational reply about the scene.
    Fall back to a deterministic human-readable summary if the LLM call fails or returns unusable text.
    """
    sys_inst = (
        "You are a concise assistant. Given a user's question about a 3D scene, the Cypher used (context only), "
        "and the query results (JSON), produce a friendly 1-2 sentence plain-English answer. "
        "If the results include distances, state them with units (meters). If there are counts, state the number clearly. "
        "If no matching data was found, say 'No matching results found.'"
    )

    # Small preview of rows to keep the prompt compact
    preview = rows[:6] if rows else []
    try:
        rows_text = json.dumps(preview, ensure_ascii=False)
    except Exception:
        rows_text = str(preview)

    prompt = (
        f"User question: {question}\n\n"
        f"Cypher executed (context only):\n{cypher}\n\n"
        f"Results preview (up to 6 rows):\n{rows_text}\n\n"
        "Now answer conversationally in plain English (1-2 sentences)."
    )

    # Try LLM first
    try:
        reply_text = call_llm(sys_inst, prompt)
        if reply_text:
            # strip codeblocks and whitespace
            reply = re.sub(r"```[\s\S]*?```", "", reply_text).strip()
            # If reply looks like JSON dump, ignore and fallback
            if reply and not reply.startswith("{"):
                return reply
    except Exception:
        # fall back below
        pass

    # Deterministic fallback summary (if LLM failed or returned unusable output)
    if not rows:
        return "No matching results found."
    # If single-row with distance-like keys -> format distance
    r0 = rows[0]
    for k in ("distance", "dist", "distance_between_door_and_sofa", "distance_between"):
        if k in r0:
            try:
                d = float(r0[k])
                return f"The distance is approximately {d:.3f} meters."
            except Exception:
                continue
    # If a count field present
    for k in ("count", "number", "num", "number_of_chairs"):
        if k in r0:
            try:
                n = int(r0[k])
                return f"There are {n} matching item(s)."
            except Exception:
                continue
    # Generic fallback: mention number of returned rows
    return f"I found {len(rows)} result(s)."


@app.post("/chat")
async def chat(req: ChatReq):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Empty question")

    cypher = ""
    cypher_params: Dict[str, Any] = {}
    llm_explain = ""
    # 1) Try to get cypher from LLM
    try:
        user_prompt = f"Scene ID: {req.scene_id}\nQuestion: {req.question}"
        raw_llm = call_llm(SYSTEM_PROMPT_GEN_CYPHER, user_prompt)
    except Exception as e:
        raw_llm = ""
        # try local fallback pattern before failing
        cy_from_pattern, explain, fb_params = fallback_pattern_cypher(req.question, req.scene_id)
        if cy_from_pattern:
            cypher = cy_from_pattern
            cypher_params = fb_params
            llm_explain = f"(fallback pattern) {explain}"
        else:
            raise HTTPException(status_code=502, detail=f"LLM error: {e}") from e
    else:
        cypher, llm_explain = extract_cypher_from_text(raw_llm)
        cypher = normalize_distance_and_sanitize(cypher)
        # if LLM didn't produce cypher, try local pattern fallback
        if not cypher:
            cy_from_pattern, explain, fb_params = fallback_pattern_cypher(req.question, req.scene_id)
            if cy_from_pattern:
                cypher = cy_from_pattern
                cypher_params = fb_params
                llm_explain = f"(fallback pattern) {explain}"

    if not cypher:
        return {"llm_text": llm_explain or "No Cypher generated", "cypher": "", "results": [], "final_answer": None, "highlight_segment_id": None}

    if not validate_cypher_readonly(cypher):
        raise HTTPException(status_code=400, detail="Generated Cypher rejected by safety rules")

    if req.scene_id and req.scene_id not in cypher:
        raise HTTPException(status_code=400, detail="Generated Cypher missing scene_id filter")

    try:
        rows = run_cypher_and_serialize(cypher, cypher_params)
    except Exception as e:
        # helpful debug info: return cypher attempted
        raise HTTPException(status_code=500, detail=f"Neo4j error: {e}. Cypher: {cypher!r}") from e

    # conservative rewrite if empty results
    if not rows:
        cy_rewrite = cypher.replace(":Object", ":PointCloudSegment").replace(":Segment ", ":PointCloudSegment ").replace("category", "semanticLabel").replace("semantic_name", "semanticLabel").replace("scene_id:", "sceneId:")
        if cy_rewrite != cypher:
            try:
                rows2 = run_cypher_and_serialize(cy_rewrite)
                if rows2:
                    rows = rows2
                    cypher = cy_rewrite
                    llm_explain = (llm_explain or "") + " (rewritten to :PointCloudSegment/semanticLabel)"
            except Exception:
                pass

    highlight_segment_id = None
    if rows:
        for v in rows[0].values():
            if isinstance(v, str) and "_sem_" in v:
                highlight_segment_id = v
                break

        # build a short machine-friendly final_answer (keeps existing behavior)
    final_answer = None
    try:
        if rows and isinstance(rows, list) and len(rows) == 1:
            r0 = rows[0]
            if "count" in r0:
                final_answer = f"{int(r0['count'])}"
            elif "number_of_chairs" in r0:
                final_answer = f"{int(r0['number_of_chairs'])}"
            elif "dist" in r0:
                d = float(r0["dist"])
                final_answer = f"{d:.3f} meters"
            elif "distance" in r0:
                d = float(r0["distance"])
                final_answer = f"{d:.3f} meters"
        if final_answer is None and rows:
            final_answer = f"Returned {len(rows)} result(s)."
    except Exception:
        final_answer = None

    # conversational reply using the LLM (with fallback)
    try:
        conversational_reply = synthesize_conversational_reply(req.question, cypher, rows)
    except Exception:
        conversational_reply = None

    return {
        "llm_text": llm_explain,
        "cypher": cypher,
        "results": rows,
        "final_answer": final_answer,
        "conversational_reply": conversational_reply,
        "highlight_segment_id": highlight_segment_id,
    }

