# online_segmentation.py

import os
import numpy as np
import torch
from neo4j import GraphDatabase

from pointnet_s3dis.src.models.pointnet import PointNetSegmentation

# --------------------------- Config ---------------------------

LABEL_MAP = {
    0: "ceiling", 1: "floor", 2: "wall", 3: "beam",
    4: "column", 5: "window", 6: "door", 7: "chair",
    8: "table", 9: "bookcase", 10: "sofa", 11: "board", 12: "clutter"
}

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")  # Required - no default for security

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ---------------------- 1. Load model once --------------------

_model = None


def get_model():
    global _model
    if _model is None:
        model = PointNetSegmentation(num_classes=13, feature_transform=True).to(device)

        here = os.path.dirname(os.path.abspath(__file__))
        # Try checkpoints folder first, then root folder
        model_path = os.path.join(here, "checkpoints", "best_pointnet_s3dis.pth")
        if not os.path.isfile(model_path):
            model_path = os.path.join(here, "best_pointnet_s3dis.pth")
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"Cannot find model at {model_path}")

        state = torch.load(model_path, map_location=device, weights_only=True)
        model.load_state_dict(state)
        model.eval()
        _model = model
    return _model


# ------------------ 2. Normalize uploaded array ----------------

def parse_uploaded_points(np_array: np.ndarray) -> np.ndarray:
    """
    Return float32 array of shape [N, 6] (xyzrgb).
    If only XYZ is provided, pad RGB with zeros.
    """
    if np_array.ndim != 2:
        raise ValueError(f"Expected 2D array, got shape {np_array.shape}")

    n_cols = np_array.shape[1]

    if n_cols == 3:
        xyz = np_array
        rgb = np.zeros_like(xyz)
        feats = np.concatenate([xyz, rgb], axis=1)
    elif n_cols >= 6:
        feats = np_array[:, :6]
    else:
        raise ValueError(
            f"Invalid point cloud shape {np_array.shape}. Must be (N,3) or (N,6)."
        )

    return feats.astype(np.float32)


# ---------------------- 3. Run PointNet ------------------------

def run_pointnet(points_np: np.ndarray, num_points: int = 4096):
    """
    points_np: [N, D] (at least xyz in first 3 columns)
    Returns:
        xyz_orig: [num_points, 3]  (original coords, for vis / Neo4j)
        labels:   [num_points]     (predicted semantic labels)
    """
    model = get_model()

    coords = points_np[:, :3].astype(np.float32)  # XYZ only (like training)
    N = coords.shape[0]

    # --- same sampling as dataset ---
    if N >= num_points:
        idx = np.random.choice(N, num_points, replace=False)
    else:
        idx = np.random.choice(N, num_points, replace=True)

    coords_sampled = coords[idx]          # [num_points, 3]
    coords_orig = coords_sampled.copy()   # keep original for output

    # --- same normalization as normalize_coords() in dataset.py ---
    centroid = np.mean(coords_sampled, axis=0)
    coords_centered = coords_sampled - centroid
    m = np.max(np.sqrt(np.sum(coords_centered ** 2, axis=1)))
    if m < 1e-6:
        m = 1.0
    coords_norm = coords_centered / m

    # to tensor [B, 3, N]
    pts = torch.from_numpy(coords_norm).unsqueeze(0)    # [1, num_points, 3]
    pts = pts.transpose(2, 1).to(device)                # [1, 3, num_points]

    with torch.no_grad():
        logits, _, _ = model(pts)                       # [1, num_points, 13]
        preds = logits.argmax(dim=2)[0].cpu().numpy()   # [num_points]

    return coords_orig, preds


def run_pointnet_multi(points_np: np.ndarray, passes: int = 8, num_points: int = 4096):
    """
    Run PointNet multiple times on different random subsets and
    concatenate results to get a denser labeled cloud.
    """
    all_xyz = []
    all_labels = []

    for _ in range(passes):
        xyz, labels = run_pointnet(points_np, num_points=num_points)
        all_xyz.append(xyz)
        all_labels.append(labels)

    xyz_full = np.concatenate(all_xyz, axis=0)      # [passes * num_points, 3]
    labels_full = np.concatenate(all_labels, axis=0)

    return xyz_full, labels_full

# -------------------- 4. Build segments & edges ----------------

# Replace your build_segments function with this (online_segmentation.py)

import numpy as np

def build_segments(points_xyz, labels):
    """
    Group points by label → summaries + edges.
    Produces bounding boxes per segment for AABB queries.
    Returns (summaries, edges)
    summaries: [{ segment_key, semantic_id, semantic_name, centroid, bbox_min, bbox_max, num_points }, ...]
    edges: fallback edges (same as before)
    """
    summaries = []
    edges = []

    unique = np.unique(labels)
    centroids = {}
    bboxes = {}

    for lbl in unique:
        mask = (labels == lbl)
        pts = points_xyz[mask]
        if pts.size == 0:
            continue

        centroid = pts.mean(axis=0)
        mins = pts.min(axis=0)
        maxs = pts.max(axis=0)

        centroids[int(lbl)] = centroid
        bboxes[int(lbl)] = (mins, maxs)

        summaries.append({
            "segment_key": int(lbl),
            "semantic_id": int(lbl),
            "semantic_name": LABEL_MAP.get(int(lbl), "unknown"),
            "centroid": centroid.tolist(),
            "bbox_min": mins.tolist(),
            "bbox_max": maxs.tolist(),
            "num_points": int(pts.shape[0]),
        })

    keys = list(centroids.keys())

    DIST_THRESHOLD = 6.0
    for i in range(len(keys)):
        for j in range(i+1, len(keys)):
            k1, k2 = keys[i], keys[j]
            c1, c2 = centroids[k1], centroids[k2]
            dist = float(np.linalg.norm(c1 - c2))
            if dist <= DIST_THRESHOLD:
                edges.append({"from": k1, "to": k2, "distance": round(dist, 3)})

    if len(edges) == 0 and len(keys) > 1:
        dists = []
        for i in range(len(keys)):
            for j in range(i+1, len(keys)):
                c1, c2 = centroids[keys[i]], centroids[keys[j]]
                dist = float(np.linalg.norm(c1 - c2))
                dists.append((dist, keys[i], keys[j]))
        dists.sort()
        top = dists[:min(5, len(dists))]
        for dist, k1, k2 in top:
            edges.append({"from": k1, "to": k2, "distance": round(dist, 3)})

    return summaries, edges


# ----------------------- 5. Neo4j writing ----------------------

def write_scene_to_neo4j(scene_id, segments, edges, uri=NEO4J_URI, user=NEO4J_USER, password=None, create_near_relationships=True):
    """
    Writes segments to Neo4j with spatial properties:
      - seg.centroid_point  => Neo4j point({x,y,z})
      - seg.centroid        => original list
      - seg.bbox_min, seg.bbox_max => arrays [x,y,z]
      - seg.bbox_center     => Neo4j point({x,y,z})
    Optionally creates NEAR relationships using edges list.
    """
    password = password or NEO4J_PASSWORD
    if not password:
        raise ValueError("NEO4J_PASSWORD environment variable is required")
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        session.run("MERGE (sc:Scene {id: $id})", id=scene_id)

        for seg in segments:
            seg_label = seg["segment_key"]
            seg_id = f"{scene_id}_sem_{seg_label}"

            cx, cy, cz = seg["centroid"]
            bbox_min = seg.get("bbox_min", seg["centroid"])
            bbox_max = seg.get("bbox_max", seg["centroid"])

            center_x = (bbox_min[0] + bbox_max[0]) / 2.0
            center_y = (bbox_min[1] + bbox_max[1]) / 2.0
            center_z = (bbox_min[2] + bbox_max[2]) / 2.0

            session.run(
                """
                MERGE (seg:Segment {id: $id})
                SET seg.scene_id = $scene_id,
                    seg.semantic_id = $semantic_id,
                    seg.semantic_name = $semantic_name,
                    seg.centroid = $centroid,
                    seg.centroid_point = point({x:$cx, y:$cy, z:$cz}),
                    seg.bbox_min = $bbox_min,
                    seg.bbox_max = $bbox_max,
                    seg.bbox_center = point({x:$center_x, y:$center_y, z:$center_z}),
                    seg.num_points = $num_points
                WITH seg
                MATCH (s:Scene {id: $scene_id})
                MERGE (seg)-[:PART_OF]->(s)
                """,
                id=seg_id,
                scene_id=scene_id,
                semantic_id=seg["semantic_id"],
                semantic_name=seg["semantic_name"],
                centroid=seg["centroid"],
                cx=float(cx), cy=float(cy), cz=float(cz),
                bbox_min=bbox_min,
                bbox_max=bbox_max,
                center_x=float(center_x), center_y=float(center_y), center_z=float(center_z),
                num_points=seg["num_points"],
            )

        if create_near_relationships and edges:
            for e in edges:
                id1 = f"{scene_id}_sem_{e['from']}"
                id2 = f"{scene_id}_sem_{e['to']}"
                dist = float(e.get("distance", 0.0))
                session.run(
                    """
                    MATCH (a:Segment {id:$id1}), (b:Segment {id:$id2})
                    MERGE (a)-[r:NEAR]-(b)
                    SET r.distance = $dist
                    """,
                    id1=id1, id2=id2, dist=dist
                )
    driver.close()


# ---------------------- 6. Public entrypoint -------------------

def process_uploaded_array(np_array: np.ndarray, scene_id: str):
    """
    Main function called from FastAPI.

    np_array: raw data from .npy/.txt (N,3) or (N,6)
    """
    feats = parse_uploaded_points(np_array)
    xyz, labels = run_pointnet_multi(feats, passes=24, num_points=8192)
    segments, edges = build_segments(xyz, labels)


    # Also write to Neo4j for downstream graph view
    write_scene_to_neo4j(scene_id, segments, edges)

    return {
        "scene_id": scene_id,
        "points": xyz.tolist(),
        "labels": labels.tolist(),
        "segments": segments,
        "edges": edges,
    }
