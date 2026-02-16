#!/usr/bin/env python3
"""Cross-validate Neo4j seeded schema against the live bSDD API."""

import json, os, sys, requests
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(Path(__file__).parent.parent / ".env")

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PWD = os.getenv("NEO4J_PASSWORD")
DB = os.getenv("NEO4J_DATABASE", "bimtwin")

BSDD_API = "https://api.bsdd.buildingsmart.org"

driver = GraphDatabase.driver(URI, auth=(USER, PWD))

# ── 1. Dump local schema ──
print("=" * 60)
print("1/3  LOCAL NEO4J DATA (database: %s)" % DB)
print("=" * 60)

with driver.session(database=DB) as s:
    # Node counts
    rows = s.run("MATCH (n) RETURN labels(n)[0] AS lbl, count(n) AS cnt ORDER BY cnt DESC").data()
    print("\nNode counts:")
    for r in rows:
        print("  %-25s %d" % (r["lbl"], r["cnt"]))

    # Constraints
    rows = s.run("SHOW CONSTRAINTS").data()
    print("\nConstraints: %d" % len(rows))
    for r in rows:
        print("  %-35s %s on %s" % (r["name"], r["type"], r["labelsOrTypes"]))

    # Indexes
    rows = s.run("SHOW INDEXES YIELD name, type, labelsOrTypes, properties WHERE type <> 'LOOKUP'").data()
    print("\nIndexes: %d" % len(rows))
    for r in rows:
        print("  %-35s %s on %s(%s)" % (r["name"], r["type"], r["labelsOrTypes"], r["properties"]))

    # Dictionaries
    dicts = s.run("MATCH (d:BsddDictionary) RETURN d {.*} AS d").data()
    print("\nDictionaries: %d" % len(dicts))
    for r in dicts:
        d = r["d"]
        print("  %s v%s [%s]  uri=%s" % (d.get("name"), d.get("version"), d.get("status"), d.get("uri")))

    # Classes
    classes = s.run("MATCH (c:BsddClass) RETURN c {.*} AS c ORDER BY c.code").data()
    print("\nClasses: %d" % len(classes))
    for r in classes:
        c = r["c"]
        print("  %-15s %-20s ifc=%s  uri=%s" % (c.get("code"), c.get("name"), c.get("relatedIfcEntities"), c.get("uri")))

    # Properties
    props = s.run("MATCH (p:BsddProperty) RETURN p {.*} AS p ORDER BY p.code").data()
    print("\nProperties: %d" % len(props))
    for r in props:
        p = r["p"]
        print("  %-25s type=%-8s units=%s  uri=%s" % (p.get("code"), p.get("dataType"), p.get("units"), p.get("uri")))

    # Relationships
    rels = s.run("MATCH (a)-[r]->(b) RETURN labels(a)[0] AS f, type(r) AS rel, labels(b)[0] AS t, count(*) AS cnt").data()
    print("\nRelationships:")
    for r in rels:
        print("  (%s)-[%s]->(%s)  x%d" % (r["f"], r["rel"], r["t"], r["cnt"]))

    # Semantic classes
    sems = s.run("MATCH (sc:SemanticClass) RETURN sc.label AS lbl, sc.classId AS cid ORDER BY sc.classId").data()
    print("\nSemantic classes: %d" % len(sems))
    for r in sems:
        print("  %2d: %s" % (r["cid"], r["lbl"]))

# ── 2. Validate against live bSDD API ──
print("\n" + "=" * 60)
print("2/3  CROSS-VALIDATE vs LIVE bSDD API (%s)" % BSDD_API)
print("=" * 60)

errors = []
warnings = []

# Validate dictionary
for r in dicts:
    d = r["d"]
    uri = d["uri"]
    print("\n[Dictionary] %s" % d["name"])
    try:
        resp = requests.get(f"{BSDD_API}/api/Dictionary/v1", params={"Uri": uri}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and "dictionaries" in data:
                matches = [x for x in data["dictionaries"] if x.get("uri") == uri]
                if matches:
                    api = matches[0]
                    print("  API name:    %s" % api.get("name"))
                    print("  API version: %s" % api.get("version"))
                    print("  Local name:  %s" % d.get("name"))
                    print("  Local ver:   %s" % d.get("version"))
                    if api.get("name") != d.get("name"):
                        warnings.append("Dictionary name mismatch: API='%s' vs Local='%s'" % (api.get("name"), d.get("name")))
                    print("  MATCH: OK")
                else:
                    errors.append("Dictionary URI not found in API response: %s" % uri)
                    print("  MATCH: NOT FOUND in API")
            else:
                print("  API returned unexpected format: %s" % str(data)[:200])
        else:
            print("  API status: %d" % resp.status_code)
            # Try alternate endpoint
            resp2 = requests.get(f"{BSDD_API}/api/Dictionary/v1/{uri}", timeout=10)
            print("  Alternate: %d" % resp2.status_code)
    except Exception as e:
        errors.append("Dictionary API error: %s" % e)
        print("  ERROR: %s" % e)

# Validate classes
for r in classes:
    c = r["c"]
    uri = c["uri"]
    code = c.get("code")
    print("\n[Class] %s (%s)" % (code, c.get("name")))
    try:
        resp = requests.get(f"{BSDD_API}/api/Class/v1", params={"Uri": uri, "includeClassProperties": "false"}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            api_name = data.get("name", "")
            api_code = data.get("code", "")
            print("  API name: %s  code: %s" % (api_name, api_code))
            print("  Local:    %s  code: %s" % (c.get("name"), code))
            if api_code and api_code != code:
                errors.append("Class code mismatch: API='%s' vs Local='%s'" % (api_code, code))
                print("  CODE MISMATCH!")
            else:
                print("  MATCH: OK")
            # Check IFC mapping
            ifc_ents = data.get("relatedIfcEntityNames", [])
            local_ifc = c.get("relatedIfcEntities", [])
            if ifc_ents:
                print("  API IFC entities: %s" % ifc_ents)
                print("  Local IFC:        %s" % local_ifc)
        else:
            errors.append("Class not found in API (HTTP %d): %s" % (resp.status_code, uri))
            print("  NOT FOUND (HTTP %d)" % resp.status_code)
    except Exception as e:
        errors.append("Class API error for %s: %s" % (code, e))
        print("  ERROR: %s" % e)

# Validate properties
for r in props:
    p = r["p"]
    uri = p["uri"]
    code = p.get("code")
    print("\n[Property] %s (%s)" % (code, p.get("name")))
    try:
        resp = requests.get(f"{BSDD_API}/api/Property/v1", params={"Uri": uri}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            api_name = data.get("name", "")
            api_code = data.get("code", "")
            print("  API name: %s  code: %s" % (api_name, api_code))
            print("  Local:    %s  code: %s" % (p.get("name"), code))
            if api_code and api_code != code:
                errors.append("Property code mismatch: API='%s' vs Local='%s'" % (api_code, code))
                print("  CODE MISMATCH!")
            else:
                print("  MATCH: OK")
        else:
            warnings.append("Property not found in API (HTTP %d): %s" % (resp.status_code, uri))
            print("  NOT FOUND (HTTP %d) — may be a synthetic property" % resp.status_code)
    except Exception as e:
        errors.append("Property API error for %s: %s" % (code, e))
        print("  ERROR: %s" % e)

# ── 3. Summary ──
print("\n" + "=" * 60)
print("3/3  VALIDATION SUMMARY")
print("=" * 60)
print("  Errors:   %d" % len(errors))
for e in errors:
    print("    [ERR] %s" % e)
print("  Warnings: %d" % len(warnings))
for w in warnings:
    print("    [WARN] %s" % w)
if not errors and not warnings:
    print("  ALL OK — schema matches bSDD API")

driver.close()
