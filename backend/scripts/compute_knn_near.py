# backend/scripts/compute_knn_near.py
"""
Improved kNN writer with diagnostics.
Usage:
  # list available scene_ids in DB
  python compute_knn_near.py --list-scenes

  # compute kNN for a specific scene (k default 5)
  python compute_knn_near.py --scene my_scene_01 --k 5

  # run with verbose prints to console
  python compute_knn_near.py --scene my_scene_01 --k 5 --verbose
"""
import os
import math
import argparse
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
if not env_path.exists():
    raise RuntimeError(f"Missing .env file at {env_path}. Copy .env.example to .env and configure.")
load_dotenv(env_path)

# All configuration from .env - no hardcoded defaults
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")

if not NEO4J_URI or not NEO4J_USER or not NEO4J_PASSWORD:
    raise RuntimeError("Missing Neo4j configuration. Set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in .env")

def connect():
    print(f"[INFO] Connecting to Neo4j at {NEO4J_URI} as {NEO4J_USER}")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return driver

def list_scenes(driver):
    with driver.session() as s:
        recs = s.run("MATCH (seg:Segment) RETURN DISTINCT seg.scene_id AS scene_id ORDER BY scene_id").values()
        scenes = [r[0] for r in recs]
    return scenes

def fetch_segments(driver, scene_id):
    with driver.session() as s:
        rows = s.run(
            "MATCH (seg:Segment {scene_id:$scene_id}) "
            "RETURN seg.id AS id, seg.centroid_point AS pt, seg.centroid AS centroid",
            scene_id=scene_id
        ).data()
    return rows

def compute_and_write_knn(driver, scene_id, k=5, verbose=False):
    rows = fetch_segments(driver, scene_id)
    total = len(rows)
    print(f"[INFO] Found {total} segments for scene_id='{scene_id}'")

    if total == 0:
        print("[WARN] No segments found for that scene_id. Check available scenes with --list-scenes")
        return

    pts = []
    for r in rows:
        pid = r["id"]
        pt = r["pt"]
        centroid_raw = r.get("centroid")
        if pt is None:
            # attempt fallback: if centroid array exists, convert it here (but do NOT modify DB)
            if centroid_raw and len(centroid_raw) >= 3:
                x, y, z = float(centroid_raw[0]), float(centroid_raw[1]), float(centroid_raw[2])
                pts.append((pid, (x, y, z)))
                if verbose:
                    print(f"[INFO] Using raw centroid for {pid}")
            else:
                if verbose:
                    print(f"[SKIP] {pid} has no centroid_point and no centroid array -> skipping")
                continue
        else:
            # centroid_point may come as dict-like or neo4j Point object
            if hasattr(pt, "x") and hasattr(pt, "y") and hasattr(pt, "z"):
                x, y, z = float(pt.x), float(pt.y), float(pt.z)
            elif isinstance(pt, dict):
                x, y, z = float(pt.get("x", 0.0)), float(pt.get("y", 0.0)), float(pt.get("z", 0.0))
            else:
                # fallback: try to interpret as list
                try:
                    x, y, z = float(pt[0]), float(pt[1]), float(pt[2])
                except Exception:
                    if verbose:
                        print(f"[SKIP] {pid} centroid_point in unknown format: {pt}")
                    continue
            pts.append((pid, (x, y, z)))

    print(f"[INFO] Using {len(pts)} points for kNN computation (k={k})")

    if len(pts) < 2:
        print("[WARN] Not enough points to compute neighbours")
        return

    # Optionally remove existing knn NEAR relations for this scene to avoid duplicates
    with driver.session() as s:
        s.run("MATCH ()-[r:NEAR {method:'knn'}]-() DELETE r")
        if verbose:
            print("[INFO] Deleted previous NEAR {method:'knn'} relationships")

    # compute distances and write neighbors
    created = 0
    for i, (id_i, pi) in enumerate(pts):
        # compute distances to others
        dists = []
        for j, (id_j, pj) in enumerate(pts):
            if id_i == id_j:
                continue
            dx = pi[0] - pj[0]; dy = pi[1] - pj[1]; dz = pi[2] - pj[2]
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            dists.append((dist, id_j))
        dists.sort(key=lambda x: x[0])
        neighbors = dists[:k]
        # write neighbors
        with driver.session() as s:
            for rank, (dist, nid) in enumerate(neighbors, start=1):
                s.run(
                    "MATCH (a:Segment {id:$id_a}), (b:Segment {id:$id_b}) "
                    "MERGE (a)-[r:NEAR {method:'knn'}]-(b) "
                    "SET r.distance = $dist, r.k_rank = $rank",
                    id_a=id_i, id_b=nid, dist=float(dist), rank=rank
                )
                created += 1
        if verbose and (i % 10 == 0 or i == len(pts)-1):
            print(f"[PROGRESS] processed {i+1}/{len(pts)} segments")

    print(f"[INFO] Created/updated approximately {created} NEAR relationships (undirected)")

    # verification counts
    with driver.session() as s:
        count_rels = s.run(
            "MATCH (a:Segment {scene_id:$scene_id})-[r:NEAR {method:'knn'}]-(b:Segment {scene_id:$scene_id}) RETURN count(r) AS cnt",
            scene_id=scene_id
        ).single().get("cnt", 0)
    print(f"[VERIFY] NEAR { 'knn' } relationships in scene '{scene_id}': {count_rels}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list-scenes", action="store_true", help="List distinct seg.scene_id values")
    parser.add_argument("--scene", type=str, help="Scene ID to compute kNN for")
    parser.add_argument("--k", type=int, default=5, help="k neighbors")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    driver = connect()

    if args.list_scenes:
        scenes = list_scenes(driver)
        print("[SCENES]")
        for s in scenes:
            print(" -", s)
        return

    if not args.scene:
        print("Error: provide --scene <scene_id> or --list-scenes")
        scenes = list_scenes(driver)
        print("Available scenes (example):")
        for s in scenes[:10]:
            print(" -", s)
        return

    compute_and_write_knn(driver, args.scene, k=args.k, verbose=args.verbose)
    driver.close()

if __name__ == "__main__":
    main()
