import os
import io
import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from neo4j import GraphDatabase, basic_auth

from pointnet_s3dis.online_segmentation import process_uploaded_array


env_path = Path(__file__).resolve().parent.parent / ".env"
if not env_path.exists():
    raise RuntimeError(f"Missing .env file at {env_path}. Copy .env.example to .env and configure.")
load_dotenv(env_path)

# All configuration from .env - no hardcoded defaults
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")

# Ollama configuration (local LLM)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # "ollama" or "gemini"

if not NEO4J_URI or not NEO4J_USER or not NEO4J_PASSWORD:
    raise RuntimeError("Missing Neo4j configuration. Set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in .env")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD))
except Exception as e:
    raise RuntimeError(f"Failed to connect to Neo4j: {e}")

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
    "Schema: (:Scene {id}), (:Segment {id, scene_id, semantic_name, centroid_point, num_points}).\n"
    "Rules: generate ONE safe READ-ONLY Cypher query only. Use label :Segment (never :Object). "
    "Use property semantic_name (never category). Use point.distance(a,b) for distances. "
    "Always include WHERE seg.scene_id = '<SCENE_ID>' when a scene_id is provided.\n\n"
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

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/health/neo4j")
def health_neo4j():
    """Basic Neo4j connectivity check (and verifies the selected database exists)."""
    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            row = session.run("RETURN 1 AS ok").single()
        return {"ok": bool(row and row.get("ok") == 1), "database": NEO4J_DATABASE, "uri": NEO4J_URI}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neo4j health check failed: {e}")

class ChatReq(BaseModel):
    question: str
    scene_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

@app.post("/upload")
async def upload_pointcloud(file: UploadFile = File(...)):
    # Check file type
    filename_lower = file.filename.lower()
    if filename_lower.endswith(('.ifc', '.rvt', '.dwg', '.dxf', '.nwd', '.nwc')):
        raise HTTPException(
            status_code=400,
            detail=f"BIM model files (.ifc, .rvt, etc.) should be uploaded via APS Viewer tab, not PointCloud tab. "
                   f"This endpoint accepts .npy point cloud files or text-based coordinate files (CSV/TXT)."
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
            )
    
    scene_id = os.path.splitext(file.filename)[0]
    return process_uploaded_array(np_array, scene_id=scene_id)

def extract_cypher_from_text(text: str) -> (str, str):
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

def run_cypher_and_serialize(cypher: str) -> List[Dict[str, Any]]:
    with driver.session(database=NEO4J_DATABASE) as session:
        results = session.run(cypher).data()
    json_rows = []
    for row in results:
        j = {}
        for k, v in row.items():
            j[k] = neo4j_json(v)
        json_rows.append(j)
    return json_rows

def fallback_pattern_cypher(question: str, scene_id: Optional[str]) -> (str, str):
    q = (question or "").lower()
    m = DIST_BETWEEN_RE.search(q)
    if m and scene_id:
        a = m.group(1).strip()
        b = m.group(2).strip()
        cy = (
            f"MATCH (a:Segment {{scene_id: '{scene_id}'}}), (b:Segment {{scene_id: '{scene_id}'}}) "
            f"WHERE toLower(a.semantic_name) CONTAINS toLower('{a}') AND toLower(b.semantic_name) CONTAINS toLower('{b}') "
            f"RETURN a.id AS a_id, b.id AS b_id, point.distance(a.centroid_point, b.centroid_point) AS dist LIMIT 10"
        )
        return cy, f"Distance between {a} and {b}"
    m2 = WITHIN_RE.search(q)
    if m2 and scene_id:
        meters = float(m2.group(2))
        target = m2.group(4).strip()
        cy = (
            f"MATCH (t:Segment {{scene_id: '{scene_id}'}}) "
            f"WHERE toLower(t.semantic_name) CONTAINS toLower('{target}') "
            f"WITH t "
            f"MATCH (o:Segment {{scene_id: '{scene_id}'}}) "
            f"WHERE o.id <> t.id AND point.distance(t.centroid_point, o.centroid_point) <= {meters} "
            f"RETURN o.id AS id, o.semantic_name AS semantic_name, point.distance(t.centroid_point, o.centroid_point) AS dist LIMIT 200"
        )
        return cy, f"Objects within {meters} m of {target}"
    m3 = COUNT_RE.search(q)
    if m3 and scene_id:
        sem = m3.group(2).strip().split()[0]
        cy = (
            f"MATCH (s:Segment {{scene_id: '{scene_id}'}}) "
            f"WHERE toLower(s.semantic_name) CONTAINS toLower('{sem}') "
            f"RETURN count(s) AS count"
        )
        return cy, f"Count of {sem}"
    m4 = LIST_RE.search(q)
    if m4 and scene_id:
        sem = m4.group(2).strip().split()[0]
        cy = (
            f"MATCH (s:Segment {{scene_id: '{scene_id}'}}) "
            f"WHERE toLower(s.semantic_name) CONTAINS toLower('{sem}') "
            f"RETURN s.id AS id, s.semantic_name AS semantic_name, s.num_points AS num_points LIMIT 200"
        )
        return cy, f"List segments matching {sem}"
    return "", ""

def call_gemini(system_instruction: str, user_prompt: str, timeout: int = 30) -> str:
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY missing in environment")
    headers = {"Content-Type": "application/json", "x-goog-api-key": GOOGLE_API_KEY}
    merged = (system_instruction.strip() + "\n\n" + user_prompt.strip()).strip()
    body = {"contents": [{"parts": [{"text": merged}]}]}
    last_err = None
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
    raise RuntimeError(f"Gemini failed: {last_err}")


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
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. Make sure Ollama is running.")
    except Exception as e:
        raise RuntimeError(f"Ollama failed: {e}")


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
    llm_explain = ""
    # 1) Try to get cypher from LLM
    try:
        user_prompt = f"Scene ID: {req.scene_id}\nQuestion: {req.question}"
        raw_llm = call_llm(SYSTEM_PROMPT_GEN_CYPHER, user_prompt)
    except Exception as e:
        raw_llm = ""
        # try local fallback pattern before failing
        cy_from_pattern, explain = fallback_pattern_cypher(req.question, req.scene_id)
        if cy_from_pattern:
            cypher = cy_from_pattern
            llm_explain = f"(fallback pattern) {explain}"
        else:
            raise HTTPException(status_code=502, detail=f"LLM error: {e}")
    else:
        cypher, llm_explain = extract_cypher_from_text(raw_llm)
        cypher = normalize_distance_and_sanitize(cypher)
        # if LLM didn't produce cypher, try local pattern fallback
        if not cypher:
            cy_from_pattern, explain = fallback_pattern_cypher(req.question, req.scene_id)
            if cy_from_pattern:
                cypher = cy_from_pattern
                llm_explain = f"(fallback pattern) {explain}"

    if not cypher:
        return {"llm_text": llm_explain or "No Cypher generated", "cypher": "", "results": [], "final_answer": None, "highlight_segment_id": None}

    if not validate_cypher_readonly(cypher):
        raise HTTPException(status_code=400, detail="Generated Cypher rejected by safety rules")

    if req.scene_id and req.scene_id not in cypher:
        raise HTTPException(status_code=400, detail="Generated Cypher missing scene_id filter")

    try:
        rows = run_cypher_and_serialize(cypher)
    except Exception as e:
        # helpful debug info: return cypher attempted
        raise HTTPException(status_code=500, detail=f"Neo4j error: {e}. Cypher: {cypher!r}")

    # conservative rewrite if empty results
    if not rows:
        cy_rewrite = cypher.replace(":Object", ":Segment").replace("category", "semantic_name").replace("scene:", "scene_id:")
        if cy_rewrite != cypher:
            try:
                rows2 = run_cypher_and_serialize(cy_rewrite)
                if rows2:
                    rows = rows2
                    cypher = cy_rewrite
                    llm_explain = (llm_explain or "") + " (rewritten to :Segment/semantic_name)"
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

